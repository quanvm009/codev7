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
        self.report_name = 'schedule_for_production'
        self.localcontext.update({
            'get_information_section': self.get_information_section,
            'get_purchase': self.get_purchase_order,
            '_get_section': self.get_section,
        })

    def get_purchase_order(self, plan):
        # Get information section
        res = {}
        material_obj = self.pool.get('production.material')
        p_l_obj = self.pool.get('purchase.order.line')
        p_l_ids = p_l_obj.search(self.cr, self.uid, [('sale_line_id', '=', plan.sale_line_id.id),
                                                     ('order_id.state', 'not in', ['draft', 'cancel'])])
        dict_no = {}
        dict_diff = {}
        for line in p_l_obj.browse(self.cr, self.uid, p_l_ids):
            add_number = False
            # set order number belong to partner and product
            if str((line.order_id.partner_id, line.product_id)) not in dict_no.keys():
                dict_no.update({str((line.order_id.partner_id, line.product_id)): 1})
                add_number = True
            else:
                dict_no[str((line.order_id.partner_id, line.product_id))] += 1
            # get quantity schedule of each material product
            qty_schedule = 0

            if add_number:
                material_ids = material_obj.search(self.cr, self.uid, [('section_material_id.plan_id', '=', plan.id),
                                                                       ('section_material_id.sequence', '=', 0),
                                                                       ('product_id', '=', line.product_id.id)])

                for schedule in material_obj.browse(self.cr, self.uid, material_ids):
                    qty_schedule += schedule.quantity

            if line.order_id.partner_id not in res.keys():
                res.update({line.order_id.partner_id: [{
                                                           'number': add_number and dict_no[
                                                               str((line.order_id.partner_id, line.product_id))] or '',
                                                           'qty_schedule': add_number and qty_schedule or '',
                                                           'product': add_number and line.product_id.name or '',
                                                           'qty_exactly': line.product_qty,
                                                           'date': line.order_id.date_order,
                                                           'amount': line.price_subtotal,
                                                           'price': line.price_unit,
                                                           'factory': '',
                                                       }]})
                dict_diff.update({line.order_id.partner_id: line.product_qty - (add_number and qty_schedule or 0)})
            else:
                res[line.order_id.partner_id].append({
                    'number': add_number and dict_no[str((line.order_id.partner_id, line.product_id))] or '',
                    'qty_schedule': add_number and qty_schedule or '',
                    'product': add_number and line.product_id.name or '',
                    'qty_exactly': line.product_qty,
                    'date': line.order_id.date_order,
                    'amount': line.price_subtotal,
                    'price': line.price_unit,
                    'factory': '',
                })
                dict_diff[line.order_id.partner_id] += line.product_qty - (add_number and qty_schedule or 0)
        return res, dict_diff

    def get_section(self, plan):
        # Get information section
        result = []
        for line in plan.section_ids:
            section = {
                'name': line.name,
                'factory': line.stock_plan_id.name,
                'norm': line.norm,
            }
            result.append(section)
        return result

    def get_product_finished(self, product_finished, price, factory, product):
        # Get information production finished
        result = []
        no = 0
        for fact in product_finished:
            for line in fact.out_finished_ids:
                if no == 0:
                    info = {
                        'number': no + 1,
                        'qty_schedule': product['qty_schedule'],
                        'product': product['product'],
                        'qty_exactly': line.quantity,
                        'date': line.date,
                        'amount': line.price_unit * line.quantity,
                        'price': line.price_unit,
                        'factory': fact.stock_id.name,
                    }
                    no += 1
                else:
                    info = {
                        'number': "",
                        'qty_schedule': "",
                        'product': "",
                        'qty_exactly': line.quantity,
                        'date': line.date,
                        'amount': line.price_unit * line.quantity,
                        'price': line.price_unit,
                        'factory': fact.stock_id.name,
                    }
                result.append(info)
        return result

    def get_total_qty(self, product_finished):
        # Get total quantity for product finished
        total_qty = 0
        for fact in product_finished:
            for line in fact.out_finished_ids:
                total_qty += line.quantity or 0
        return total_qty

    def get_total_amount(self, product_finished, price):
        # Get total amount for product finished
        total_amount = 0
        for fact in product_finished:
            for line in fact.out_finished_ids:
                total_amount += line.quantity * price or 0
        return total_amount

    def get_information_section(self, plan):
        # Get information section
        result = []
        if plan.section_ids:
            for line in plan.section_ids:
                product = {
                    'number': line.sequence,
                    'qty_schedule': line.qty,
                    'product': line.product_id.name,
                    'total_quantity': self.get_total_qty(line.history_fact_ids)
                }

                section = {
                    'qty_schedule': line.qty,
                    'total_qty': product['total_quantity'],
                    'total_amount': self.get_total_amount(line.history_fact_ids, line.price),
                    'qty_difference': line.qty - product['total_quantity'],
                    'product_finished': self.get_product_finished(line.history_fact_ids, line.price, line.stock_id.name,
                                                                  product),
                    'description': line.description,
                    'name': '%s Factory' % line.name,
                }
                result.append(section)
        return result

