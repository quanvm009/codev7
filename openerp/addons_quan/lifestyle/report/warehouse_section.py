# #############################################################################
#
# Copyright (c) 2008-2011 Alistek Ltd (http://www.alistek.com) All Rights Reserved.
# General contacts <info@alistek.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This module is GPLv3 or newer and incompatible
# with OpenERP SA "AGPL + Private Use License"!
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################


import datetime
from itertools import groupby
import math
from operator import itemgetter
import time

from dateutil import parser
from dateutil import relativedelta
from openerp import netsvc
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
from report import report_sxw
from report.report_sxw import rml_parse


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'sale_order': self.get_sale_order,
            'section': self.get_section,
            'factory': self.get_factory,
            'lines': self.get_infor_report,
            'total': self.get_total,
            'tong_all': self.get_tong_all,
            #####
            'get_tong_all': self.get_tong_all,
            'get_nha_may': self.get_nha_may,
            'get_date_done': self.get_date_done,
            'get_color': self.get_color,
            'get_move': self.get_move,
            'get_tong': self.get_tong,
        })


    def get_sale_order(self, sale_id):
        return self.pool.get('sale.order').browse(self.cr, self.uid, sale_id)

    def get_section(self, section_id):
        return self.pool.get('init.section').browse(self.cr, self.uid, section_id)

    def get_factory(self, warehouse_id):
        return self.pool.get('stock.warehouse').browse(self.cr, self.uid, warehouse_id)


    def get_nha_may(self, form):
        cr = self.cr
        uid = self.uid
        detail = []
        dict = {}
        picking_obj = self.pool.get('stock.picking')
        lst_picking = picking_obj.search(cr, uid, [('sale_id', '=', form['sale_id'][0]),
                                                   ('state', '=', 'done')
                                                   ], order='date_done')
        for picking in picking_obj.browse(cr, uid, lst_picking):
            dict = {
                'init_warehouse_id': picking and picking.init_warehouse_id and picking.init_warehouse_id.id or False,
                'name': picking and picking.init_warehouse_id and picking.init_warehouse_id.name or ''
            }
            if dict not in detail:
                detail.append(dict)
        return detail

    def get_date_done(self, form, init_warehouse_id):
        cr = self.cr
        uid = self.uid
        detail = []
        dict = {}
        picking_obj = self.pool.get('stock.picking')
        lst_picking = picking_obj.search(cr, uid, [('init_warehouse_id', '=', init_warehouse_id),
                                                   ('sale_id', '=', form['sale_id'][0]),
                                                   ('state', '=', 'done')
                                                   ], order='date_done')
        for picking in picking_obj.browse(cr, uid, lst_picking):
            dict = {'date_done': picking.date_done[0:10]
                    }
            if dict not in detail:
                detail.append(dict)
        return detail

    def get_color(self, form, date, init_warehouse_id):
        cr = self.cr
        uid = self.uid
        detail = []
        date_from = '%s 00:00:00' % date
        date_to = '%s 23:59:59' % date
        move_obj = self.pool.get('stock.move')
        lst_move = move_obj.search(cr, uid, [('picking_id.init_warehouse_id', '=', init_warehouse_id),
                                             ('picking_id.sale_id', '=', form['sale_id'][0]),
                                             ('state', '=', 'done'),
                                             ('date', '>', date_from),
                                             ('date', '<', date_to)
                                             ])
        # lst_color = [(move.color_id and move.color_id.id or False) for move in move_obj.browse(cr, uid, lst_move)]
        lst_color = []
        for move in move_obj.browse(cr, uid, lst_move):
            if move.color_id:
                lst_color.append(move.color_id.id)
        lst_color = list(set(lst_color))
        for color in lst_color:
            stt = 1
            kg = 0
            yard = 0
            amount_kg = 0
            roll = 0
            candoi_kg = 0
            candoi_yard = 0
            move_ids = move_obj.search(cr, uid, [('id', 'in', lst_move),
                                                 ('color_id', '=', color)
                                                 ])
            for move in move_obj.browse(cr, uid, move_ids):
                yard += move.qty_kg or 0
                kg += move.product_qty or 0
                amount_kg += (move.product_qty * move.processing_price) or 0
                roll += move.roll and (int(move.roll)) or 0
                if stt != 1:
                    candoi_kg += move.product_qty
                    candoi_yard += move.qty_kg
                else:
                    candoi_kg = move.product_qty - move.qty_kg_real
                    candoi_yard = move.qty_kg - move.qty_yrd_real
                stt += 1
                dict = {
                    'color_id': move.color_id and move.color_id.id or False,
                    'name': move.color_id and move.color_id.name or '',
                    'kg': kg,
                    'yard': yard,
                    'candoi_kg': candoi_kg,
                    'candoi_yard': candoi_yard,
                    'amount_kg': amount_kg,
                    'roll': roll,
                    'weight': move.weight or '',
                    'width': move.width or '',
                    'qty_kg_real': move.qty_kg_real or 0,
                    'qty_yrd_real': move.qty_yrd_real or 0,
                }
            detail.append(dict)
        return detail

    def get_move(self, form, date, color_id, init_warehouse_id):
        cr = self.cr
        uid = self.uid
        detail = []
        move_obj = self.pool.get('stock.move')
        date_from = '%s 00:00:00' % date
        date_to = '%s 23:59:59' % date
        lst_move = move_obj.search(cr, uid, [('picking_id.init_warehouse_id', '=', init_warehouse_id),
                                             ('picking_id.sale_id', '=', form['sale_id'][0]),
                                             ('state', '=', 'done'),
                                             ('color_id', '=', color_id),
                                             ('date', '>', date_from),
                                             ('date', '<', date_to)
                                             ])
        for move in move_obj.browse(cr, uid, lst_move):
            dict = {'picking': move.picking_id and move.picking_id.name or '',
                    'qty_kg_real': move.qty_kg_real or 0,
                    'qty_yrd_real': move.qty_yrd_real or 0,
                    'lot': move.lot or '',
                    'roll': move.roll or '',
                    'weight': move.weight or '',
                    'width': move.width or '',
                    'kg': move.product_qty or 0,
                    'yard': move.qty_kg or 0,
                    'address': move.address or '',
                    'note': move.note or '',
                    'price_unit': move.price_unit or '',
                    'process_price': move.processing_price or '',
                    }
            detail.append(dict)
        return detail

    def get_tong(self, form, init_warehouse_id):
        cr = self.cr
        uid = self.uid
        detail = []
        kg = 0
        yard = 0
        kg_real = 0
        yard_real = 0
        amount_kg = 0
        roll = 0
        picking_obj = self.pool.get('stock.picking')
        lst_picking = picking_obj.search(cr, uid, [('init_warehouse_id', '=', init_warehouse_id),
                                                   ('sale_id', '=', form['sale_id'][0]),
                                                   ('state', '=', 'done')
                                                   ])

        for picking in picking_obj.browse(cr, uid, lst_picking):
            for move in picking.move_lines:
                yard += move.qty_kg or 0
                kg += move.product_qty or 0
                yard_real += move.qty_yrd_real or 0
                kg_real += move.qty_kg_real or 0
                amount_kg += (move.product_qty * move.processing_price) or 0
                roll += move.roll and (int(move.roll)) or 0

        dict = {'yard': yard,
                'kg': kg,
                'yard_real': yard_real,
                'kg_real': kg_real,
                'amount_kg': amount_kg,
                'roll': roll,
                }
        detail.append(dict)
        return detail

    def get_tong_all(self, form):
        cr = self.cr
        uid = self.uid
        detail = []
        kg = 0
        yard = 0
        kg_real = 0
        yard_real = 0
        amount_kg = 0
        roll = 0
        picking_obj = self.pool.get('stock.picking')
        lst_picking = picking_obj.search(cr, uid, [
            ('sale_id', '=', form['sale_id'][0]),
            ('state', '=', 'done')
        ])
        for picking in picking_obj.browse(cr, uid, lst_picking):
            for move in picking.move_lines:
                yard += move.qty_kg or 0
                kg += move.product_qty or 0
                yard_real += move.qty_kg_real or 0
                kg_real += move.qty_yrd_real or 0

                amount_kg += (move.product_qty * move.processing_price) or 0
                roll += move.roll and (int(move.roll)) or 0

        dict = {'yard': yard,
                'kg': kg,
                'yard_real': yard_real,
                'kg_real': kg_real,
                'amount_kg': amount_kg,
                'roll': roll,
                }
        detail.append(dict)
        return detail


    ########################################

    def get_infor_report(self, form):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        move_obj = self.pool.get('stock.move')
        sale_obj = self.pool.get('sale.order')
        product_ids = [line.product_id.id for line in sale_obj.browse(cr, uid, form['sale_id'][0]).order_line]
        section_ids = section_obj.search(cr, uid, [('section_config_id', '=', form['section_id'][0]),
                                                   ('plan_id.sale_line_id.order_id', '=', form['sale_id'][0])])
        move_ids = move_obj.search(cr, uid, [('sale_line_id.order_id', '=', form['sale_id'][0]),
                                             ('section_id', '=', False),
                                             ('product_id', 'in', product_ids),
                                             ('state', '=', 'done')])
        detail = []
        no = 0
        material_in, finish_in, finish_in_kg = 0, 0, 0
        for section in section_obj.browse(cr, uid, section_ids):

            for material in section.material_ids:
                material_in += material.quantity

            for finish in section.finished_ids:
                finish_in += finish.quantity
                finish_in_kg += finish.qty_kg

        amount = 0
        lst_color = [move.color_id and move.color_id.id for move in move_obj.browse(cr, uid, move_ids)]
        lst_color = list(set(lst_color))
        for color in lst_color:
            qty, qty_yrd = 0, 0
            for move in move_obj.browse(cr, uid, move_ids):
                if move.color_id.id == color:
                    no += 1
                    qty += move.product_qty
                    qty_yrd += move.qty_kg
                    dict = {'no': no,
                            'product': move.product_id.name,
                            'code': move.sale_line_id.categ_id.name,
                            'color': move.color_id.name,
                            'material_in': material_in,
                            'finish_in': finish_in,
                            'finish_in_kg': finish_in_kg,
                            # 'missing_qty': finish_in - qty,
                            'missing_qty': move.qty_yrd_real - qty_yrd,
                            'missing_qty_kg': move.qty_kg_real - qty,
                            'amount': amount,
                            'lines': detail,
                            'lot': move.lot or '',
                            'roll': move.roll or '',
                            'weight': move.weight or '',
                            'width': move.width or '',
                            'note': move.note,
                            'date': move.date and time.strftime('%d/%m/%Y',
                                                                time.strptime(move.date, '%Y-%m-%d %H:%M:%S')) or '',
                            'yard': move.product_qty,
                            'price_unit': move.price_unit,
                            'amount': move.price_unit * move.qty_kg,
                            'kg': move.qty_kg or 0,
                            'qty_kg_real': move.qty_kg_real or 0,
                            'qty_yrd_real': move.qty_yrd_real or 0,
                            }
                    detail.append(dict)
        return detail

    def get_total(self, form):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        move_obj = self.pool.get('stock.move')
        sale_obj = self.pool.get('sale.order')
        product_ids = [line.product_id.id for line in sale_obj.browse(cr, uid, form['sale_id'][0]).order_line]
        section_ids = section_obj.search(cr, uid, [('section_config_id', '=', form['section_id'][0]),
                                                   ('plan_id.sale_line_id.order_id', '=', form['sale_id'][0])])
        move_ids = move_obj.search(cr, uid, [('sale_line_id.order_id', '=', form['sale_id'][0]),
                                             ('section_id', '=', False),
                                             ('product_id', 'in', product_ids),
                                             ('state', '=', 'done')])
        detail = []
        no = 0
        material_in, finish_in, finish_in_kg = 0, 0, 0
        for section in section_obj.browse(cr, uid, section_ids):

            for material in section.material_ids:
                material_in += material.quantity

            for finish in section.finished_ids:
                finish_in += finish.quantity
                finish_in_kg += finish.qty_kg

        qty, amount, qty_yrd = 0, 0, 0
        for move in move_obj.browse(cr, uid, move_ids):
            qty += move.product_qty
            qty_yrd += move.qty_kg
            amount += move.price_unit * move.qty_kg
        dict = {
            'code': '.',
            # 'code': move.sale_line_id.categ_id.name,
            'material_in': material_in,
            'finish_in': finish_in,
            'finish_in_kg': finish_in_kg,
            # 'missing_qty': finish_in - qty,
            'yard': qty,
            'kg': qty_yrd,
            'amount': amount,
        }
        detail.append(dict)
        return detail


# def get_infor_report(self, form):
# cr = self.cr
# uid = self.uid
# section_obj = self.pool.get('production.section')
# section_ids = section_obj.search(cr,uid, [('section_config_id','=', form['section_id'][0]),
# ('plan_id.sale_line_id.order_id','=', form['sale_id'][0])])
# detail = []
# no = 0
#
# for section in section_obj.browse(cr, uid, section_ids):
# if section.history_fact_ids:
# no += 1
#             count = 0
#
#             material_in,finish_in,finish_in_kg = 0,0,0
#             for material in section.material_ids:
#                 material_in += material.quantity
#
#             for finish in section.finished_ids:
#                 finish_in += finish.quantity
#                 finish_in_kg += finish.qty_kg
#
#             qty, amount = 0,0
#             for line in section.history_fact_ids:
#                 if line.stock_id.id == form['warehouse_id'][0]:
#                     lst_history = []
#                     if line.out_finished_ids:
#                         lst_history = line.out_finished_ids
#                     else:
#                         lst_history = line.in_finished_ids
#
#                     for finish in lst_history:
#                         qty += finish.quantity
#                         amount += finish.quantity * finish.price_unit
#
#             for line in section.history_fact_ids:
#                 if line.stock_id.id == form['warehouse_id'][0]:
#                     for finish in lst_history:
#                         dict = {'no': '',
#                                 'product': '',
#                                 'code': '',
#                                 'color': '',
#                                 'material_in': '',
#                                 'finish_in': '',
#                                 'finish_in_kg':'',
#                                 'missing_qty': '',
#                                 'amount': '',
#                                 'lines': '',
#                                 }
#                         if count == 0:
#                             dict = {'no': no,
#                                     'product': section.plan_id.sale_line_id.product_id.name,
#                                     'code': section.plan_id.sale_line_id.code,
#                                     'color': section.plan_id.sale_line_id.color_id.name,
#                                     'material_in': material_in,
#                                     'finish_in': finish_in,
#                                     'finish_in_kg': finish_in_kg,
#                                     'missing_qty': finish_in - qty,
#                                     'amount': amount,
#                                     'lines': detail
#                                     }
#                         dict.update({
#                                        'lot': finish.move_id and finish.move_id.lot or '',
#                                        'roll': finish.move_id and finish.move_id.roll or '',
#                                        'weight': finish.move_id and finish.move_id.weight or '',
#                                        'width': finish.move_id and finish.move_id.width or '',
#                                        'date': finish.date,
#                                        'yard': finish.quantity,
#                                        'price_unit': finish.price_unit,
#                                        'amount': finish.price_unit * finish.quantity,
#                                        'kg': finish.qty_kg or 0,
#                                        })
#                         detail.append(dict)
#                         count += 1
#
#
#         return detail

#     def get_total(self, form):
#         cr = self.cr
#         uid = self.uid
#         section_obj = self.pool.get('production.section')
#         section_ids = section_obj.search(cr, uid, [('section_config_id', '=', form['section_id'][0]),
#                                                   ('plan_id.sale_line_id.order_id', '=', form['sale_id'][0])])
#         material_in, finish_in, finish_in_kg = 0, 0, 0
#         detail_finish_in, detail_finish_in_kg, amount = 0, 0, 0
#
#         for section in section_obj.browse(cr, uid, section_ids):
#
#             flag = False
#             qty, amount = 0, 0
#             for line in section.history_fact_ids:
#                 if line.stock_id.id == form['warehouse_id'][0]:
#                     lst_history = []
#                     if line.out_finished_ids:
#                         lst_history = line.out_finished_ids
#                     else:
#                         lst_history = line.in_finished_ids
#
#                     for finish in lst_history:
#                         flag = True
#                         detail_finish_in += finish.quantity
#                         detail_finish_in_kg += finish.qty_kg
#                         amount += finish.quantity * finish.price_unit
#
#             if flag:
#                 for material in section.material_ids:
#                     material_in += material.quantity
#
#                 for finish in section.finished_ids:
#                     finish_in += finish.quantity
#                     finish_in_kg += finish.qty_kg
#
#         return [{'no': '',
#                 'product': '',
#                 'code': '',
#                 'color': '',
#                 'material_in': material_in,
#                 'finish_in': finish_in,
#                 'finish_in_kg': finish_in_kg,
#                 'missing_qty': finish_in - detail_finish_in,
#                 'amount': amount,
#                 'lines': '',
#                 'yard': detail_finish_in,
#                 'price_unit': detail_finish_in,
#                 'kg': detail_finish_in_kg
#                 }]









