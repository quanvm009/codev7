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
# #####################################################################

import time

from report import report_sxw


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.report_name = 'schedule_for_production'
        self.localcontext.update({
            # ### Chuyen tu nha may den nha may
            'get_material_out': self.get_material_out,
            'get_material_out_detail': self.get_material_out_detail,
            'get_material_out_detail_factory': self.get_material_out_detail_factory,
            'get_material_out_total': self.get_material_out_total,
            # ### Xuat san suat
            'get_material_out_production': self.get_material_out_production,
            'get_material_out_production_total': self.get_material_out_production_total,
            'get_material_out_production_detail': self.get_material_out_production_detail,
            # ### Nhap thanh pham
            'get_data_section': self.get_data_section,
            'get_data_section_detail': self.get_data_section_detail,
            'get_data_section_detail_factory': self.get_data_section_detail_factory,
            'get_data_section_total': self.get_data_section_total,

            'get_origin_qty': self.get_origin_quantity,
            'get_qty_kg': self.get_quantity_kg,
            'get_material': self.get_material,
            # ### xem ton kho
            'get_product_ton': self.get_product_ton,
            'get_warehouse_ton': self.get_warehouse_ton,
            'get_qty_ton': self.get_qty_ton,
            # ### Lay NVL
            'get_material_detail': self.get_material_detail,
            'get_material_total': self.get_material_total,


            '_get_section': self.get_section,
            'get_out_customer': self.get_out_customer,
            'sum_get_out_customer': self.sum_get_out_customer,
            'get_other_expense': self.get_other_expense,
            'get_sum_other_expense': self.get_sum_other_expense,
        })

    def get_quantity_kg(self, so):
        qty = 0
        for line in so.order_line:
            qty += line.qty_kg
        return qty

    def get_origin_quantity(self, so):
        qty = 0
        for line in so.order_line:
            qty += line.product_uom_qty
        return qty

    def get_section(self, so):
        # Get information section
        cr = self.cr
        uid = self.uid
        result = []
        sol_ids = [line.id for line in so.order_line]
        plan_obj = self.pool.get('production.plan')
        plan_ids = plan_obj.search(cr, uid,
                                   [('sale_line_id', 'in', sol_ids), ('state', 'not in', ('draft', 'cancel'))])
        section_ids = []
        for plan in plan_obj.browse(cr, uid, plan_ids):
            for line in plan.section_ids:
                if line.section_config_id not in section_ids:
                    factory = ''
                    for his in line.history_fact_ids:
                        if his.stock_id.name not in factory:
                            if not factory:
                                factory = his.stock_id.name
                            else:
                                factory = '%s, %s' % (factory, his.stock_id.name)
                    section = {
                        'name': line.name,
                        'id': line.id,
                        'section_config_id': line.section_config_id.id,
                        'factory': factory,
                    }
                    section_ids += [line.section_config_id]
                    result.append(section)
                else:
                    dic = result[section_ids.index(line.section_config_id)]
                    factory = dic['factory']
                    for his in line.history_fact_ids:
                        if his.stock_id.name not in factory:
                            if not factory:
                                factory = his.stock_id.name
                            else:
                                factory = '%s, %s' % (factory, his.stock_id.name)
                    result[section_ids.index(line.section_config_id)]['factory'] = factory
        return result

    def get_material(self, so, company):
        cr = self.cr
        uid = self.uid
        line_ids = [line.id for line in so.order_line]

        material_obj = self.pool.get('production.material')
        p_l_obj = self.pool.get('purchase.order.line')
        stk_move_obj = self.pool.get('stock.move')

        p_l_ids = p_l_obj.search(cr, uid, [('sale_line_id', 'in', line_ids),
                                           ('order_id.state', 'not in', ['draft', 'cancel'])])
        dict_no = {}
        for line in p_l_obj.browse(cr, uid, p_l_ids):
            if line.product_id not in dict_no.keys():
                qty_schedule = 0
                plan_obj = self.pool.get('production.plan')
                plan_ids = plan_obj.search(cr, uid,
                                           [('sale_line_id', 'in', line_ids), ('state', 'not in', ('draft', 'cancel'))])
                if plan_ids:
                    material_ids = material_obj.search(cr, uid,
                                                       [('section_material_id.plan_id', 'in', plan_ids),
                                                        ('section_material_id.sequence', '=', 0),
                                                        ('product_id', '=', line.product_id.id)])
                    if not material_ids:
                        material_ids = material_obj.search(cr, uid,
                                                           [('section_material_id.plan_id', 'in', plan_ids),
                                                            ('section_material_id.sequence', '=', 1),
                                                            ('product_id', '=', line.product_id.id)])

                    for schedule in material_obj.browse(cr, uid, material_ids):
                        qty_schedule += schedule.quantity

                stk_move_ids = stk_move_obj.search(cr, uid, [('purchase_line_id', '=', line.id),
                                                             ('product_id', '=', line.product_id.id),
                                                             ('state', '=', 'done'),
                                                             ('picking_id.type', '=', 'in')])
                for mv in stk_move_obj.browse(cr, uid, stk_move_ids):
                    if line.product_id not in dict_no.keys():
                        dict_no.update({
                            line.product_id: {
                                'number': 0,
                                'qty_schedule': qty_schedule,
                                'product': line.product_id.name or '',
                                'qty_exactly': mv.product_qty,
                                'date': '',
                                'factory': '',
                                'product_id': line.product_id,
                            }
                        })
                    else:
                        dict_no[line.product_id]['qty_exactly'] += mv.product_qty
            else:
                stk_move_ids = stk_move_obj.search(cr, uid, [('purchase_line_id', '=', line.id),
                                                             ('state', '=', 'done'),
                                                             ('product_id', '=', line.product_id.id),
                                                             ('picking_id.type', '=', 'in')])
                for mv in stk_move_obj.browse(cr, uid, stk_move_ids):
                    dict_no[line.product_id]['qty_exactly'] += mv.product_qty
        print 'dict_no',
        number = 1
        res = []
        for key in dict_no.keys():
            dict_no[key].update({'number': number})
            res.append(dict_no[key])
            number += 1
        return res

    def get_material_total(self, so, company):
        cr = self.cr
        uid = self.uid
        line_ids = [line.id for line in so.order_line]

        material_obj = self.pool.get('production.material')
        p_l_obj = self.pool.get('purchase.order.line')
        stk_move_obj = self.pool.get('stock.move')

        p_l_ids = p_l_obj.search(cr, uid, [('sale_line_id', 'in', line_ids),
                                           ('order_id.state', 'not in', ['draft', 'cancel'])])
        dict_no = {}
        for line in p_l_obj.browse(cr, uid, p_l_ids):
            if line.product_id not in dict_no.keys():

                qty_schedule = 0
                plan_obj = self.pool.get('production.plan')
                plan_ids = plan_obj.search(cr, uid,
                                           [('sale_line_id', 'in', line_ids), ('state', 'not in', ('draft', 'cancel'))])
                if plan_ids:
                    material_ids = material_obj.search(cr, uid,
                                                       [('section_material_id.plan_id', 'in', plan_ids),
                                                        ('section_material_id.sequence', '=', 0),
                                                        ('product_id', '=', line.product_id.id)])
                    if not material_ids:
                        material_ids = material_obj.search(cr, uid,
                                                           [('section_material_id.plan_id', 'in', plan_ids),
                                                            ('section_material_id.sequence', '=', 1),
                                                            ('product_id', '=', line.product_id.id)])

                    for schedule in material_obj.browse(cr, uid, material_ids):
                        qty_schedule += schedule.quantity

                stk_move_ids = stk_move_obj.search(cr, uid, [('purchase_line_id', '=', line.id),
                                                             ('product_id', '=', line.product_id.id),
                                                             ('state', '=', 'done'),
                                                             ('picking_id.type', '=', 'in')])
                for mv in stk_move_obj.browse(cr, uid, stk_move_ids):
                    if line.product_id not in dict_no.keys():
                        dict_no.update({
                            line.product_id: {
                                'number': 0,
                                'qty_schedule': qty_schedule,
                                'product': line.product_id.name or '',
                                'qty_exactly': mv.product_qty,
                                'date': '',
                                'factory': '',
                                'product_id': line.product_id,
                            }
                        })
                    else:
                        dict_no[line.product_id]['qty_exactly'] += mv.product_qty
            else:
                stk_move_ids = stk_move_obj.search(cr, uid, [('purchase_line_id', '=', line.id),
                                                             ('product_id', '=', line.product_id.id),
                                                             ('picking_id.type', '=', 'in'),
                                                             ('state', '=', 'done'), ])
                for mv in stk_move_obj.browse(cr, uid, stk_move_ids):
                    dict_no[line.product_id]['qty_exactly'] += mv.product_qty
        res = []
        total_qty_schedule = 0
        total_qty_exactly = 0

        for key in dict_no.keys():
            total_qty_schedule += dict_no[key]['qty_schedule']
            total_qty_exactly += dict_no[key]['qty_exactly']
        res.append({
            'qty_schedule': total_qty_schedule,
            'qty_exactly': total_qty_exactly,

        })
        return res

    def get_material_detail(self, so, product, company):
        cr = self.cr
        uid = self.uid
        line_ids = [line.id for line in so.order_line]
        p_l_obj = self.pool.get('purchase.order.line')
        stk_move_obj = self.pool.get('stock.move')
        warehouse_obj = self.pool.get('stock.warehouse')

        p_l_ids = p_l_obj.search(cr, uid, [('sale_line_id', 'in', line_ids),
                                           ('product_id', '=', product.id),
                                           ('order_id.state', 'not in', ['draft', 'cancel'])])
        dict_no = []
        for line in p_l_obj.browse(cr, uid, p_l_ids):
            price_unit = 0
            stk_move_ids = stk_move_obj.search(cr, uid, [('purchase_line_id', '=', line.id),
                                                         ('state', '=', 'done'),
                                                         ('product_id', '=', line.product_id.id),
                                                         ('picking_id.type', '=', 'in')])
            for mv in stk_move_obj.browse(cr, uid, stk_move_ids):
                warehouse_ids = warehouse_obj.search(cr, uid, [('lot_stock_id', '=', mv.location_dest_id.id)])
                name_factory = warehouse_ids and warehouse_ids[0] and warehouse_obj.browse(cr, uid,
                                                                                           warehouse_ids[
                                                                                               0]).name or '????'
                dict_no.append({
                    'number': '',
                    'qty_schedule': '',
                    'product': '',
                    'qty_exactly': mv.product_qty,
                    'date': mv.date,
                    'amount': price_unit * mv.product_qty,
                    'price': price_unit,
                    'factory': name_factory,
                    'supplier': mv.picking_id and mv.picking_id.partner_id and mv.picking_id.partner_id.name or '', })
        return dict_no

    def get_avg_price(self, so, company, product_id):
        cr = self.cr
        uid = self.uid
        line_ids = [line.id for line in so.order_line]
        material_obj = self.pool.get('production.material')
        p_l_obj = self.pool.get('purchase.order.line')
        p_l_ids = p_l_obj.search(cr, uid, [('sale_line_id', 'in', line_ids),
                                           ('product_id', '=', product_id),
                                           ('order_id.state', 'not in', ['draft', 'cancel'])])
        dict_no = {}
        for line in p_l_obj.browse(cr, uid, p_l_ids):
            if line.product_id not in dict_no.keys():
                price_unit = 0
                for invl in line.invoice_lines:
                    if invl.product_id == line.product_id:
                        price_unit = self.pool.get('res.currency').compute(cr, uid,
                                                                           invl.invoice_id.currency_id.id,
                                                                           company.currency_id.id, invl.price_unit)
                        break

                qty_schedule = 0
                plan_obj = self.pool.get('production.plan')
                plan_ids = plan_obj.search(cr, uid,
                                           [('sale_line_id', 'in', line_ids), ('state', 'not in', ('draft', 'cancel'))])
                if plan_ids:
                    material_ids = material_obj.search(cr, uid,
                                                       [('section_material_id.plan_id', 'in', plan_ids),
                                                        ('section_material_id.sequence', '=', 0),
                                                        ('product_id', '=', line.product_id.id)])

                    for schedule in material_obj.browse(cr, uid, material_ids):
                        qty_schedule += schedule.quantity

                dict_no.update({line.product_id: {'qty_exactly': line.product_qty,
                                                  'amount': price_unit * line.product_qty,
                }
                })
            else:
                dict_no[line.product_id]['qty_exactly'] += line.product_qty
                dict_no[line.product_id]['amount'] += price_unit * line.product_qty

        return dict_no

    # ### Chuyen tu nha may den nha may
    def get_material_out(self, so, company, section):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_config_id = [section['section_config_id']]
        section_ids = section_obj.search(cr, uid,
                                         [('section_config_id', 'in', section_config_id), ('sale_id', '=', so.id)])
        dict_no = {}
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.in_material_ids:
                    if line.product_id not in dict_no.keys():
                        dict_no.update({
                            line.product_id: {
                                'number': 0,
                                'qty_schedule': 0,
                                'product': line.product_id.name or '',
                                'qty_exactly': line.quantity,
                                'date': '',
                                'amount': '',
                                'price': 0,
                                'factory': '',
                                'product_id': line.product_id,
                            }
                        })
                    else:
                        dict_no[line.product_id]['qty_exactly'] += line.quantity
        number = 1
        res = []
        for key in dict_no.keys():
            dict_no[key].update({'number': number})
            vals = self.get_avg_price(so, company, key.id)
            if key in vals.keys():
                price = vals[key]['amount'] / vals[key]['qty_exactly']
                dict_no[key].update({'amount': dict_no[key]['qty_exactly'] * price})
            res.append(dict_no[key])
            number += 1
        return res

    def get_material_out_total(self, so, company, section):
        cr = self.cr
        uid = self.uid
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_config_id = [section['section_config_id']]
        section_ids = section_obj.search(cr, uid,
                                         [('section_config_id', 'in', section_config_id), ('sale_id', '=', so.id)])
        dict_no = {}
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.in_material_ids:
                    if line.product_id not in dict_no.keys():
                        dict_no.update({
                            line.product_id: {
                                'qty_schedule': 0,
                                'product': line.product_id.name or '',
                                'qty_exactly': line.quantity,
                                'factory': '',
                                'product_id': line.product_id,
                            }
                        })
                    else:
                        dict_no[line.product_id]['qty_exactly'] += line.quantity
        res = []
        total_qty_schedule = 0
        total_qty_exactly = 0

        for key in dict_no.keys():
            total_qty_schedule += dict_no[key]['qty_schedule']
            total_qty_exactly += dict_no[key]['qty_exactly']
        res.append({
            'qty_schedule': total_qty_schedule,
            'qty_exactly': total_qty_exactly,

        })
        return res

    def get_material_out_detail(self, so, product, company, section):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_config_id = [section['section_config_id']]
        section_ids = section_obj.search(cr, uid,
                                         [('section_config_id', 'in', section_config_id), ('sale_id', '=', so.id)])
        dict_no = []
        lst_temp = []
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                if his.stock_id.id not in lst_temp:
                    lst_temp.append(his.stock_id.id)
                    dict_no.append({
                        'factory': his.stock_id.name,
                        'factory_id': his.stock_id.id,
                    })
        return dict_no

    def get_material_out_detail_factory(self, so, product, company, section, factory_id):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_config_id = [section['section_config_id']]
        section_ids = section_obj.search(cr, uid,
                                         [('section_config_id', 'in', section_config_id), ('sale_id', '=', so.id)])
        dict_no = []
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.in_material_ids:
                    if product == line.product_id:
                        vals = self.get_avg_price(so, company, line.product_id.id)
                        price = 0
                        if line.product_id in vals.keys():
                            price = vals[line.product_id]['amount'] / vals[line.product_id]['qty_exactly']
                        if his.stock_id.id == factory_id:
                            dict_no.append({
                                'number': '',
                                'qty_schedule': '',
                                'product': '',
                                'qty_exactly': line.quantity,
                                'roll': line.roll or 0,
                                'date': line.date,
                                'amount': line.quantity * price,
                                'price': price,
                                'factory': his.stock_id.name,
                                'factory_to': line.warehouse_id and line.warehouse_id.name or '',
                                'inv': '',
                            })
        return dict_no

    # ### Xuat san suat
    def get_material_out_production(self, so, company, section):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_config_id = [section['section_config_id']]
        section_ids = section_obj.search(cr, uid,
                                         [('section_config_id', 'in', section_config_id), ('sale_id', '=', so.id)])
        dict_no = {}
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.out_material_ids:
                    if line.product_id not in dict_no.keys():
                        dict_no.update({line.product_id: {
                            'number': 0,
                            'qty_schedule': 0,
                            'product': line.product_id.name or '',
                            'qty_exactly': line.quantity,
                            'date': '',
                            'amount': '',
                            'price': 0,
                            'factory': '',
                            'product_id': line.product_id,
                        }
                        })
                    else:
                        dict_no[line.product_id]['qty_exactly'] += line.quantity
        number = 1
        res = []
        for key in dict_no.keys():
            dict_no[key].update({'number': number})
            vals = self.get_avg_price(so, company, key.id)
            if key in vals.keys():
                price = vals[key]['amount'] / vals[key]['qty_exactly']
                dict_no[key].update({'amount': dict_no[key]['qty_exactly'] * price})
            res.append(dict_no[key])
            number += 1
        return res

    def get_material_out_production_total(self, so, company, section):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_config_id = [section['section_config_id']]
        section_ids = section_obj.search(cr, uid,
                                         [('section_config_id', 'in', section_config_id), ('sale_id', '=', so.id)])
        dict_no = {}
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.out_material_ids:
                    if line.product_id not in dict_no.keys():
                        dict_no.update({line.product_id: {
                            'qty_schedule': 0,
                            'product': line.product_id.name or '',
                            'qty_exactly': line.quantity,
                            'factory': '',
                            'product_id': line.product_id,
                        }
                        })
                    else:
                        dict_no[line.product_id]['qty_exactly'] += line.quantity
        res = []
        total_qty_schedule = 0
        total_qty_exactly = 0

        for key in dict_no.keys():
            total_qty_schedule += dict_no[key]['qty_schedule']
            total_qty_exactly += dict_no[key]['qty_exactly']
        res.append({
            'qty_schedule': total_qty_schedule,
            'qty_exactly': total_qty_exactly,

        })
        return res

    def get_material_out_production_detail(self, so, product, company, section):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_config_id = [section['section_config_id']]
        section_ids = section_obj.search(cr, uid,
                                         [('section_config_id', 'in', section_config_id), ('sale_id', '=', so.id)])
        dict_no = []
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.out_material_ids:
                    if product == line.product_id:
                        vals = self.get_avg_price(so, company, line.product_id.id)
                        price = 0
                        if line.product_id in vals.keys():
                            price = vals[line.product_id]['amount'] / vals[line.product_id]['qty_exactly']
                        dict_no.append({
                            'number': '',
                            'qty_schedule': '',
                            'product': '',
                            'qty_exactly': line.quantity,
                            'date': line.date,
                            'roll': line.roll or '',
                            'amount': line.quantity * price,
                            'price': price,
                            'factory': his.stock_id.name,
                            'factory_to': line.warehouse_id and line.warehouse_id.name or '',
                            'inv': '',

                        })
        return dict_no

    # ### Nhap thanh pham
    def get_data_section(self, so, section_config_id, company):
        cr = self.cr
        uid = self.uid
        line_ids = [line.id for line in so.order_line]
        section_obj = self.pool.get('production.section')
        plan_obj = self.pool.get('production.plan')
        plan_ids = plan_obj.search(cr, uid,
                                   [('sale_line_id', 'in', line_ids), ('state', 'not in', ('draft', 'cancel'))])
        section_ids = section_obj.search(cr, uid, [('plan_id', 'in', plan_ids),
                                                   ('section_config_id', 'in', [section_config_id])])
        dict_no = {}
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.in_finished_ids:
                    price_unit = 0
                    inv = ''
                    if line.move_id.invoice_line_id:
                        invl = line.move_id.invoice_line_id
                        price_unit = self.pool.get('res.currency').compute(cr, uid,
                                                                           invl.invoice_id.currency_id.id,
                                                                           company.currency_id.id, invl.price_unit)

                    if line.product_id not in dict_no.keys():
                        dict_no.update({line.product_id: {
                            'number': '',
                            'qty_schedule': section.qty,
                            'product': line.product_id.name,
                            'qty_exactly': line.quantity,
                            'date': '',
                            'amount': price_unit * line.quantity,
                            'product_id': line.product_id,
                            'price': 0,
                            'factory': '',
                            'inv': '',

                        }})
                    else:
                        dict_no[line.product_id]['qty_exactly'] += line.quantity
                        dict_no[line.product_id]['amount'] += (price_unit * line.quantity)
        number = 1
        res = []
        for key in dict_no.keys():
            dict_no[key].update({'number': number})
            res.append(dict_no[key])
            number += 1
        return res

    def get_data_section_total(self, so, section_config_id, company):
        cr = self.cr
        uid = self.uid
        line_ids = [line.id for line in so.order_line]
        section_obj = self.pool.get('production.section')
        plan_obj = self.pool.get('production.plan')
        plan_ids = plan_obj.search(cr, uid,
                                   [('sale_line_id', 'in', line_ids), ('state', 'not in', ('draft', 'cancel'))])
        section_ids = section_obj.search(cr, uid, [('plan_id', 'in', plan_ids),
                                                   ('section_config_id', 'in', [section_config_id])])
        dict_no = {}
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.in_finished_ids:

                    if line.product_id not in dict_no.keys():
                        dict_no.update({line.product_id: {
                            'qty_schedule': section.qty,
                            'product': line.product_id.name,
                            'qty_exactly': line.quantity,
                            'date': '',
                            'product_id': line.product_id,

                        }})
                    else:
                        dict_no[line.product_id]['qty_exactly'] += line.quantity
        res = []
        total_qty_schedule = 0
        total_qty_exactly = 0
        for key in dict_no.keys():
            total_qty_schedule += dict_no[key]['qty_schedule']
            total_qty_exactly += dict_no[key]['qty_exactly']
        res.append({
            'qty_schedule': total_qty_schedule,
            'qty_exactly': total_qty_exactly,
        })
        return res


    def get_data_section_detail(self, so, section_config_id, product, company):
        cr = self.cr
        uid = self.uid
        line_ids = [line.id for line in so.order_line]
        section_obj = self.pool.get('production.section')
        plan_obj = self.pool.get('production.plan')
        plan_ids = plan_obj.search(cr, uid,
                                   [('sale_line_id', 'in', line_ids), ('state', 'not in', ('draft', 'cancel'))])
        section_ids = section_obj.search(cr, uid, [('plan_id', 'in', plan_ids),
                                                   ('product_id', '=', product.id),
                                                   ('section_config_id', 'in', [section_config_id])])
        dict_no = []
        lst_temp = []
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                if his.stock_id.id not in lst_temp:
                    lst_temp.append(his.stock_id.id)
                    dict_no.append({
                        'factory': his.stock_id.name,
                        'factory_id': his.stock_id.id,
                    })
        return dict_no


    def get_data_section_detail_factory(self, so, section_config_id, product, factory_id, company):
        cr = self.cr
        uid = self.uid
        line_ids = [line.id for line in so.order_line]
        section_obj = self.pool.get('production.section')
        plan_obj = self.pool.get('production.plan')
        plan_ids = plan_obj.search(cr, uid,
                                   [('sale_line_id', 'in', line_ids), ('state', 'not in', ('draft', 'cancel'))])
        section_ids = section_obj.search(cr, uid, [('plan_id', 'in', plan_ids),
                                                   ('product_id', '=', product.id),
                                                   ('section_config_id', 'in', [section_config_id])])
        dict_no = []
        for section in section_obj.browse(cr, uid, section_ids):
            for his in section.history_fact_ids:
                for line in his.in_finished_ids:
                    price_unit = 0
                    inv = ''
                    if line.move_id.invoice_line_id:
                        invl = line.move_id.invoice_line_id
                        price_unit = self.pool.get('res.currency').compute(cr, uid,
                                                                           invl.invoice_id.currency_id.id,
                                                                           company.currency_id.id, invl.price_unit)
                        inv = invl.invoice_id.supplier_invoice_number or invl.invoice_id.origin
                    if his.stock_id.id == factory_id:
                        dict_no.append({
                            'number': '',
                            'qty_schedule': '',
                            'product': line.product_id.name,
                            'qty_exactly': line.quantity,
                            'date': line.date,
                            'roll': line.roll or '',
                            'amount': price_unit * line.quantity,
                            'price': price_unit,
                            'factory': his.stock_id.name,
                            'inv': inv, })
        return dict_no

    def get_other_expense(self, so, company):
        cr = self.cr
        uid = self.uid
        invl_obj = self.pool.get('account.invoice.line')
        crrency_obj = self.pool.get('res.currency')
        invl_ids = invl_obj.search(cr, uid, [('sale_id', '=', so.id),
                                             # ('invoice_id.type','=', 'in_invoice'),
                                             ('invoice_id.state', 'not in', ('draft', 'cancel'))])
        dict_no = []
        no = 0
        for invl in invl_obj.browse(cr, uid, invl_ids):
            price_unit = crrency_obj.compute(cr, uid, invl.invoice_id.currency_id.id, company.currency_id.id,
                                             invl.price_unit)
            amount = crrency_obj.compute(cr, uid, invl.invoice_id.currency_id.id, company.currency_id.id,
                                         invl.price_subtotal)
            inv = invl.invoice_id.supplier_invoice_number or invl.invoice_id.origin or invl.invoice_id.number
            no += 1
            dict_no.append({
                'number': no,
                'product': invl.name,
                'date': invl.invoice_id.date_invoice,
                'qty': invl.quantity,
                'uos': invl.uos_id and invl.uos_id.name or '',
                'amount_customer': invl.invoice_id.type == 'out_invoice' and amount or 0,
                'amount_supplier': invl.invoice_id.type == 'in_invoice' and amount or 0,
                'price': price_unit,
                'inv': inv,
            })
        return dict_no

    def get_sum_other_expense(self, so, company):
        cr = self.cr
        uid = self.uid
        invl_obj = self.pool.get('account.invoice.line')
        crrency_obj = self.pool.get('res.currency')
        invl_ids = invl_obj.search(cr, uid, [('sale_id', '=', so.id),
                                             # ('invoice_id.type','=', 'in_invoice'),
                                             ('invoice_id.state', 'not in', ('draft', 'cancel'))])
        dict_no = []
        qty = 0
        amount_customer = 0
        amount_supplier = 0
        for invl in invl_obj.browse(cr, uid, invl_ids):
            amount = crrency_obj.compute(cr, uid, invl.invoice_id.currency_id.id, company.currency_id.id,
                                         invl.price_subtotal)
            qty += invl.quantity
            amount_customer += invl.invoice_id.type == 'out_invoice' and amount or 0
            amount_supplier += invl.invoice_id.type == 'in_invoice' and amount or 0
        dict_no.append({
            'qty': qty,
            'amount_customer': amount_customer,
            'amount_supplier': amount_supplier,
        })
        return dict_no

    def get_out_customer(self, so, company):
        cr = self.cr
        uid = self.uid
        stk_move_obj = self.pool.get('stock.move')
        dict_no = []
        for line in so.order_line:
            price_unit, no = 0, 0
            inv = ''
            for invl in line.invoice_lines:
                if invl.product_id == line.product_id:
                    # price_unit = self.pool.get('res.currency').compute(cr, uid,
                    # invl.invoice_id.currency_id.id,
                    # company.currency_id.id, invl.price_unit)
                    inv = invl.invoice_id.number or invl.invoice_id.origin
                    break

            stk_move_ids = stk_move_obj.search(cr, uid, [('sale_line_id', '=', line.id),
                                                         ('picking_id.sale_id', '=', so.id),
                                                         ('picking_id.type', '=', 'out'),
                                                         ('state', '=', 'done')])
            for mv in stk_move_obj.browse(cr, uid, stk_move_ids):
                no += 1
                dict_no.append({
                    'number': no,
                    'product': '[%s]%s' % (mv.product_id.categ_id.name, mv.product_id.name),
                    'color': mv.color_id and mv.color_id.name or '',
                    'date': mv.picking_id and mv.picking_id.date_done and time.strftime('%d/%m/%Y', time.strptime(
                        mv.picking_id.date_done, '%Y-%m-%d %H:%M:%S')) or '',
                    'qty': mv.product_qty,
                    'roll': mv.roll or '',
                    'address': mv.address or '',
                    'note': mv.note or '',
                    'amount': mv.product_qty * mv.price_unit,
                    'price': mv.price_unit,
                    'inv': inv,
                    'location_name': mv.location_id and mv.location_id.name or '',
                })
        return dict_no

    def sum_get_out_customer(self, so, company):
        cr = self.cr
        uid = self.uid
        stk_move_obj = self.pool.get('stock.move')
        dict_no = []
        for line in so.order_line:
            stk_move_ids = stk_move_obj.search(cr, uid, [('sale_line_id', '=', line.id),
                                                         ('picking_id.sale_id', '=', so.id),
                                                         ('picking_id.type', '=', 'out'),
                                                         ('state', '=', 'done')])
            qty = 0
            roll = 0
            amount = 0
            for mv in stk_move_obj.browse(cr, uid, stk_move_ids):
                qty += mv.product_qty or 0
                amount += mv.product_qty * mv.price_unit
                # roll += int(mv.roll) or 0
                roll += (mv.roll and int(mv.roll)) or 0
            dict_no.append({
                'qty': qty,
                'roll': roll,
                'amount': amount,
            })
        return dict_no


    # ### lay ton kho
    def get_product_ton(self, section):
        cr = self.cr
        uid = self.uid
        move_obj = self.pool.get('stock.move')
        res = []
        lst_product = []
        lst_move = move_obj.search(cr, uid, [('section_id', '=', section['id'])])
        for line in move_obj.browse(cr, uid, lst_move):
            if line.product_id not in lst_product:
                lst_product.append(line.product_id)
                res.append({
                    'name': line.product_id.name,
                    'product_id': line.product_id.id
                })
        return res

    def get_warehouse_ton(self, section):
        cr = self.cr
        uid = self.uid
        move_obj = self.pool.get('stock.move')
        res = []
        lst_location = []
        lst_move = move_obj.search(cr, uid, [('section_id', '=', section['id'])])
        for line in move_obj.browse(cr, uid, lst_move):
            if line.location_dest_id.usage == 'internal' and line.location_dest_id not in lst_location:
                lst_location.append(line.location_dest_id)
                res.append({
                    'name': line.location_dest_id.name,
                    'location_id': line.location_dest_id.id
                })
            if line.location_id.usage == 'internal' and line.location_id not in lst_location:
                lst_location.append(line.location_id)
                res.append({
                    'name': line.location_id.name,
                    'location_id': line.location_id.id
                })
        return res

    def get_qty_ton(self, o, product_id, location_id):
        cr = self.cr
        uid = self.uid
        product_obj = self.pool.get('product.product')
        move_obj = self.pool.get('stock.move')
        qty = 0
        if product_id and location_id:
            lst_move_in = move_obj.search(cr, uid, [('sale_id', '=', o.id), ('product_id', '=', product_id),
                                                    ('location_id', '=', location_id)])
            lst_move_out = move_obj.search(cr, uid, [('sale_id', '=', o.id), ('product_id', '=', o.id),
                                                     ('location_dest_id', '=', location_id)])

            qty += sum([line.product_qty or 0 for line in move_obj.browse(cr, uid, lst_move_in)])
            qty -= sum([line.product_qty or 0 for line in move_obj.browse(cr, uid, lst_move_out)])
        return qty

