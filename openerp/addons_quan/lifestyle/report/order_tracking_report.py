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
from openerp.report import report_sxw


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.report_name = 'order_tracking_report'
        self.localcontext.update({
            'get_customer': self.get_customer,
            'get_factory': self.get_factory,
            'get_date_send_order': self.get_date_send_order,
            'get_date_delivery': self.get_date_delivery,
            'order_detail': self.order_detail,
            'total_quantity': self.get_total_quantity,
            'total_after_dye': self.get_total_after_dye,
            'total_yard': self.get_total_yard,
            'total_yard_de': self.get_total_yard_de,
            'total_kg': self.get_total_kg,
            'total_loss': self.get_total_loss,
            'total_money': self.get_total_money,
            'code_order': self.get_code_order,
        })
        self.total_quantity = 0.0
        self.total_after_dye = 0.0
        self.total_yard = 0.0
        self.total_yard_de = 0.0
        self.total_kg = 0.0
        self.total_loss = 0.0
        self.total_money = 0.0

    def get_date_send_order(self, data):
        order_obj = self.pool.get('sale.order')
        order = order_obj.browse(self.cr, self.uid, data['form']['sale_id'][0])
        return order.date_send_order

    def get_date_delivery(self, data):
        order_obj = self.pool.get('sale.order')
        order = order_obj.browse(self.cr, self.uid, data['form']['sale_id'][0])
        return order.date_delivery

    def get_customer(self, data):
        #Get customer
        order_obj = self.pool.get('sale.order')
        order = order_obj.browse(self.cr, self.uid, data['form']['sale_id'][0])
        return order.partner_id.name

    def get_factory(self, data):
        #Get warehouse
        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse = warehouse_obj.browse(self.cr, self.uid, data['form']['stock_id'][0])
        return warehouse.partner_id.name

    def get_total_qty_move_line(self, stock_ids):
        #Get total quantity for product finished
        move_obj = self.pool.get('stock.move')
        sum_kg = 0
        for stock in move_obj.browse(self.cr, self.uid, stock_ids):
            sum_kg += stock.product_qty
        return sum_kg

    def picking_detail(self, product, stock_ids, product_detail):
        move_obj = self.pool.get('stock.move')
        first = True
        result = []
        for stock in move_obj.browse(self.cr, self.uid, stock_ids):
            if first:
                detail = {
                    'numbers': product['numbers'],
                    'product_name': product['product_name'],
                    'product_code': product['product_code'],
                    'color': product_detail['color'],
                    'quantity': product_detail['quantity'],
                    'after_dyes': product_detail['after_dyes'],
                    'yard': product_detail['yard'],
                    'list_price': product_detail['list_price'],
                    'loss': product_detail['loss'],
                    'money': product_detail['money'],
                    'lot': stock.lot,
                    'roll': stock.roll,
                    'kg': stock.product_qty,
                    'width': stock.product_id.width,
                    'weight': stock.product_id.weight_prod,
                    'date': stock.date,
                    'yard_de': stock.qty_kg
                }
                self.total_quantity += product_detail['quantity']
                self.total_after_dye += product_detail['after_dyes']
                self.total_yard += product_detail['yard']
                self.total_yard_de += stock.qty_kg
                self.total_kg += stock.product_qty
                self.total_loss += product_detail['loss']
                self.total_money += product_detail['money']
                first = False
            else:
                detail = {
                    'numbers': "",
                    'product_name': "",
                    'product_code': "",
                    'color': "",
                    'quantity': "",
                    'after_dyes': "",
                    'yard': "",
                    'list_price': "",
                    'loss': "",
                    'money': "",
                    'lot': stock.lot,
                    'roll': stock.roll,
                    'kg': stock.product_qty,
                    'width': stock.product_id.width,
                    'weight': stock.product_id.weight_prod,
                    'date': stock.date,
                    'yard_de': stock.qty_kg
                }
                self.total_yard_de += stock.qty_kg
                self.total_kg += stock.product_qty
            result.append(detail)
        return result

    def order_detail(self, data):
        order_line_obj = self.pool.get('sale.order.line')
        plan_obj = self.pool.get('production.plan')
        section_obj = self.pool.get('production.section')
        stock_move_obj = self.pool.get('stock.move')
        material_obj = self.pool.get('production.material')
        product_obj = self.pool.get('product.product')
        warehouse_obj = self.pool.get('stock.warehouse')
        order_line_ids = order_line_obj.search(self.cr, self.uid, [('order_id', '=', data['form']['sale_id'][0])])
        warehouse = warehouse_obj.browse(self.cr, self.uid, data['form']['stock_id'][0])
        result = []
        old_product_id = 0
        numbers = 0
        for line in order_line_obj.browse(self.cr, self.uid, order_line_ids):
            plan_id = plan_obj.search(self.cr, self.uid, [('sale_line_id', '=', line.id)])
            section_ids = section_obj.search(self.cr, self.uid,
                                             [('plan_id', '=', plan_id[0]),
                                              ('stock_id', '=', data['form']['stock_id'][0])])
            stock_ids = stock_move_obj.search(self.cr, self.uid,
                                              [('section_id', '=', section_ids), ('state', '=', 'done'),
                                               ('location_dest_id', '=', warehouse.lot_input_id.id)])
            section = section_obj.browse(self.cr, self.uid, section_ids[0])
            material_ids = material_obj.search(self.cr, self.uid, [('section_material_id', '=', section_ids[0])])
            sum_kg = self.get_total_qty_move_line(section_ids)
            total_qty, total_qty_kg = 0, 0
            for line_material in material_obj.browse(self.cr, self.uid, material_ids):
                total_qty += line_material.quantity
                total_qty_kg += line_material.qty_kg
                product_section = product_obj.browse(self.cr, self.uid, line_material.product_id.id)
            if old_product_id != product_section.id:
                numbers += 1
                product = {
                    'product_name': product_section.name,
                    'product_code': product_section.code,
                    'numbers': numbers,
                }
                old_product_id = product_section.id
            else:
                product = {
                    'product_name': "",
                    'product_code': "",
                    'numbers': ""
                }
            detail_sec = {
                'color': product_section.color_id.name,
                'quantity': total_qty,
                'after_dyes': total_qty / section.norm,
                'yard': total_qty_kg,
                'list_price': product_section.list_price,
                'loss': (total_qty / section.norm) - sum_kg,
                'money': (total_qty / section.norm) * product_section.list_price
            }
            picking_detail = {'picking_product': self.picking_detail(product, stock_ids, detail_sec)}
            result.append(picking_detail)
        return result

    def get_total_quantity(self):
        return self.total_quantity

    def get_total_after_dye(self):
        return self.total_after_dye

    def get_total_yard(self):
        return self.total_yard

    def get_total_yard_de(self):
        return self.total_yard_de

    def get_total_kg(self):
        return self.total_kg

    def get_total_loss(self):
        return self.total_loss

    def get_total_money(self):
        return self.total_money

    def get_code_order(self, data):
        order_line_obj = self.pool.get('sale.order.line')
        plan_obj = self.pool.get('production.plan')
        section_obj = self.pool.get('production.section')
        stock_move_obj = self.pool.get('stock.move')
        material_obj = self.pool.get('production.material')
        product_obj = self.pool.get('product.product')
        warehouse_obj = self.pool.get('stock.warehouse')
        order_line_ids = order_line_obj.search(self.cr, self.uid, [('order_id', '=', data['form']['sale_id'][0])])
        warehouse = warehouse_obj.browse(self.cr, self.uid, data['form']['stock_id'][0])
        old_product_id = 0
        name_customer = self.get_customer(data)
        for line in order_line_obj.browse(self.cr, self.uid, order_line_ids):
            plan_id = plan_obj.search(self.cr, self.uid, [('sale_line_id', '=', line.id)])
            section_ids = section_obj.search(self.cr, self.uid,
                                             [('plan_id', '=', plan_id[0]),
                                              ('stock_id', '=', data['form']['stock_id'][0])])
            material_ids = material_obj.search(self.cr, self.uid, [('section_material_id', '=', section_ids[0])])
            total_qty = 0
            for line_material in material_obj.browse(self.cr, self.uid, material_ids):
                total_qty += line_material.quantity
                product_section = product_obj.browse(self.cr, self.uid, line_material.product_id.id)
                if old_product_id != product_section.id:
                    name_customer = '%s %s /' % (name_customer, product_section.code)
                    old_product_id = product_section.id

        return name_customer