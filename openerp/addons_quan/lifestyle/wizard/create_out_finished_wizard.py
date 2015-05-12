# -*- coding: utf-8 -*- 
# #####################################################################
# 
# OpenERP, Open Source Management Solution 
# Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>). 
# Copyright (C) 2013 INIT Tech Co., Ltd (http://init.vn). 
# This program is free software: you can redistribute it and/or modify 
# it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version. 
# 
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
# GNU Affero General Public License for more details. 
# 
# You should have received a copy of the GNU Affero General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>. 
# 
######################################################################

import time
from openerp.addons.lifestyle.model.datetime_utils import *

from dateutil.relativedelta import relativedelta
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.float_utils import float_is_zero
from openerp.tools.translate import _
from openerp import netsvc
from operator import itemgetter


class create_out_finished_wizard(osv.osv_memory):
    _name = "create.out.finished.wizard"

    def default_get(self, cr, uid, fields, context):
        if context is None:
            context = {}
        res = super(create_out_finished_wizard, self).default_get(cr, uid, fields, context=context)
        obj_plan = self.pool.get('production.plan').browse(cr, uid, context['active_ids'][0])
        result = []
        dic = {
            'product_id': obj_plan.product_id and obj_plan.product_id.id or False,
            'product_uom': obj_plan.product_id.uom_id and obj_plan.product_id.uom_id.id or False,
            'quantity': obj_plan.quantity or 0,
            'price_unit': 0,
        }
        result.append(dic)
        res['stock_id'] = obj_plan.sale_line_id.order_id.shop_id.warehouse_id.id
        res['finished_ids'] = result
        return res

    _columns = {
        'date_order': fields.date('Date', required=True),
        'note': fields.char('Note', szie=256),
        'stock_id': fields.many2one('stock.warehouse', 'To Warehouse ', required=True),
        'from_stock_id': fields.many2one('stock.warehouse', 'From Warehouse ', required=True),
        'finished_ids': fields.one2many('production.out.finished.wizard', 'finished_out_id', 'Finished'),

    }

    def onchange_warehouse_from(self, cr, uid, ids, warehouse_id, context):
        if not warehouse_id:
            return {'value': {}}

        cr.execute("""SELECT p_s1.id 
                FROM production_section p_s1
                LEFT JOIN  production_plan p_l1 ON (p_l1.id = p_s1.plan_id)
                WHERE p_l1.id = '%s' and p_s1.sequence = (SELECT  MAX(p_s.sequence)
                FROM production_section p_s
                LEFT JOIN  production_plan p_l ON (p_l.id = p_s.plan_id)
                WHERE p_l.id = '%s') """ % (context['active_ids'][0], context['active_ids'][0]))
        section_id = map(itemgetter(0), cr.fetchall())

        fact_ids = self.pool.get('history.factory').search(cr, uid, [('stock_id', '=', warehouse_id),
                                                                     ('section_fact_id', '=', section_id)])
        fact_id = fact_ids and fact_ids[0] or False
        if not fact_id:
            raise osv.except_osv(_('Error!'), _('There is no quantity in this warehouse'))

        obj_plan = self.pool.get('production.plan').browse(cr, uid, context['active_ids'][0])
        dic = {
            'product_id': obj_plan.product_id and obj_plan.product_id.id or False,
            'product_uom': obj_plan.product_id.uom_id and obj_plan.product_id.uom_id.id or False,
            'quantity': obj_plan.quantity or 0,
            'price_unit': 0,
        }
        for line in self.pool.get('history.factory').browse(cr, uid, fact_id).out_finished_ids:
            if line.product_id == obj_plan.product_id:
                dic['quantity'] -= line.quantity

        return {'value': {'finished_ids': [dic]}}

    def button_validate(self, cr, uid, ids, context={}):
        obj_material = self.browse(cr, uid, ids)[0]
        obj_plan = self.pool.get('production.plan').browse(cr, uid, context['active_ids'][0])
        wf_service = netsvc.LocalService("workflow")
        cr.execute("""SELECT p_s1.id 
                FROM production_section p_s1
                LEFT JOIN  production_plan p_l1 ON (p_l1.id = p_s1.plan_id)
                WHERE p_l1.id = '%s' and p_s1.sequence = (SELECT  MAX(p_s.sequence)
                FROM production_section p_s
                LEFT JOIN  production_plan p_l ON (p_l.id = p_s.plan_id)
                WHERE p_l.id = '%s') """ % (context['active_ids'][0], context['active_ids'][0]))
        section_id = map(itemgetter(0), cr.fetchall())

        fact_ids = self.pool.get('history.factory').search(cr, uid,
                                                           [('stock_id', '=', int(obj_material.from_stock_id.id)),
                                                            ('section_fact_id', '=', section_id)])
        fact_id = fact_ids and fact_ids[0] or False
        if not fact_id:
            raise osv.except_osv(_('Error!'), _('There is no warehouse'))

        ################################
        # Create delivery from factory to Lifestyle
        ################################
        p_out_id = self.pool.get('stock.picking').create(cr, uid, {
        'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out'),
        'date': obj_material.date_order,
        'type': 'out',
        })

        sale_line_id = obj_plan.sale_line_id.id or False
        location_id_out = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'customer')])[0]
        for line in obj_material.finished_ids:
            new_move_id = self.pool.get('stock.move').create(cr, uid, {'name': obj_material.note or '/',
                                                                       'note': obj_material.note or '/',
                                                                       'product_id': line.product_id and line.product_id.id or False,
                                                                       'product_qty': line.quantity or 0,
                                                                       'product_uom': line.product_uom and line.product_uom.id or False,
                                                                       'price_unit': line.product_id and line.product_id.list_price or 0,
                                                                       'location_id': obj_material.from_stock_id and \
                                                                                      obj_material.from_stock_id.lot_stock_id.id or False,
                                                                       'location_dest_id': location_id_out,
                                                                       'picking_id': p_out_id,
                                                                       'sale_line_id': sale_line_id,
                                                                       'color_id': obj_plan.sale_line_id.color_id \
                                                                                   and obj_plan.sale_line_id.color_id.id or False,
                                                                       'lot': line.lot or '',
                                                                       'roll': line.roll or '',
                                                                       'width': line.width or '',
                                                                       'weight': line.weight or '',
            })
            self.pool.get('history.factory.detail').create(cr, uid, {
            'product_id': line.product_id and line.product_id.id or False,
            'quantity': line.quantity or 0,
            'user_id': uid,
            'date': obj_material.date_order or False,
            'type': 'out_finished',
            'factory_id': fact_id,
            'price_unit': line.price_unit,
            'move_id': new_move_id
            })
        wf_service.trg_validate(uid, 'stock.picking', p_out_id, 'button_confirm', cr)
        self.pool.get('stock.picking').action_move(cr, uid, [p_out_id], context=context)
        wf_service.trg_validate(uid, 'stock.picking', p_out_id, 'button_done', cr)

        ################################
        # Create Incoming Shipment from Supplier's location to Factroy's location
        ################################
        p_in_id = self.pool.get('stock.picking').create(cr, uid, {
        'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in'),
        'date': obj_material.date_order,
        'type': 'in',
        })

        sale_line_id = obj_plan.sale_line_id.id or False
        location_id_in = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'supplier')])[0]
        for line in obj_material.finished_ids:
            self.pool.get('stock.move').create(cr, uid, {'name': obj_material.note or '/',
                                                         'note': obj_material.note or '/',
                                                         'product_id': line.product_id and line.product_id.id or False,
                                                         'product_qty': line.quantity or 0,
                                                         'product_uom': line.product_uom and line.product_uom.id or False,
                                                         'price_unit': line.product_id and line.product_id.list_price or 0,
                                                         'location_id': location_id_in,
                                                         'location_dest_id': obj_material.stock_id and \
                                                                             obj_material.stock_id.lot_stock_id.id or False,
                                                         'picking_id': p_in_id,
                                                         'sale_line_id': sale_line_id,
                                                         'color_id': obj_plan.sale_line_id.color_id \
                                                                     and obj_plan.sale_line_id.color_id.id or False,
                                                         'lot': line.lot or '',
                                                         'roll': line.roll or '',
                                                         'width': line.width or '',
                                                         'weight': line.weight or '',
            })
        wf_service.trg_validate(uid, 'stock.picking', p_in_id, 'button_confirm', cr)
        wf_service.trg_validate(uid, 'stock.picking', p_in_id, 'button_done', cr)

        return {
            'name': _('Income Shipping Order'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'domain': "[('id','in',%s)]" % [p_out_id, p_in_id]
        }


create_out_finished_wizard()


class production_out_finished_wizard(osv.osv_memory):
    _name = "production.out.finished.wizard"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'quantity': fields.float('Quantity'),
        'price_unit': fields.float('Price Unit'),
        'product_uom': fields.many2one('product.uom', 'UoM', required=True),
        'finished_out_id': fields.many2one('create.out.finished.wizard', 'Finished'),
        'lot': fields.text('Lot', size=32),
        'roll': fields.text('Roll', size=32),
        'width': fields.float('Width', size=32),
        'weight': fields.float('Weight', size=32)
    }
    _defaults = {
    }


production_out_finished_wizard()


