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
from openerp import netsvc
from openerp.osv import fields
from openerp.osv import osv

import openerp.addons.decimal_precision as dp


class sale_order(osv.osv):
    _inherit = 'sale.order'


    def _total_finish_qty(self, cr, uid, ids, field_names, arg, context=None):
        # Tinh tong so luong thanh pham sau khi san xuat
        move_obj = self.pool.get('stock.move')
        res = {}
        for obj in self.browse(cr, uid, ids):
            total = 0
            for line in obj.order_line:
                move_lst = move_obj.search(cr, uid, [('product_id', '=', line.product_id.id),
                                                     ('sale_line_id', '=', line.id),
                                                     ('location_id.usage', '=', 'production')])

                total += sum([f.product_qty for f in move_obj.browse(cr, uid, move_lst)])
            res[obj.id] = total
        return res

    def _total_qty(self, cr, uid, ids, field_names, arg, context=None):
        # Tinh tong so luong trn So
        res = {}
        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.order_line:
                total += sum([f.product_uom_qty for f in obj.order_line])
            res[obj.id] = total
        return res

    def _total_qty_kg(self, cr, uid, ids, field_names, arg, context=None):
        # Tinh tong so luong yard trn So
        res = {}
        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.order_line:
                total += sum([f.qty_kg for f in obj.order_line])
            res[obj.id] = total
        return res

    def _delivery_qty(self, cr, uid, ids, field_names, arg, context=None):
        # Tinh tong so luong giao hang
        res = {}
        move_obj = self.pool.get('stock.move')
        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.order_line:
                for line in obj.order_line:
                    lst_move = move_obj.search(cr, uid, [('state', '=', 'done'),
                                                         ('picking_id.init_warehouse_id', '!=', False),
                                                         ('sale_id', '=', obj.id),
                                                         ('product_id', '=', line.product_id.id),
                                                         ('location_dest_id.usage', '=', 'customer'),
                                                         ])
                    total += sum([f.product_qty for f in move_obj.browse(cr, uid, lst_move)])
            res[obj.id] = total
        return res

    def _delivery_qty_kg(self, cr, uid, ids, field_names, arg, context=None):
        # Tinh tong so luong kg giao hang
        res = {}
        move_obj = self.pool.get('stock.move')
        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.order_line:
                for line in obj.order_line:
                    lst_move = move_obj.search(cr, uid, [('state', '=', 'done'),
                                                         ('picking_id.init_warehouse_id', '!=', False),
                                                         ('sale_id', '=', obj.id),
                                                         ('product_id', '=', line.product_id.id),
                                                         ('location_dest_id.usage', '=', 'customer'),
                                                         ])
                    total += sum([f.qty_kg for f in move_obj.browse(cr, uid, lst_move)])
            res[obj.id] = total
        return res

    def _amount_real(self, cr, uid, ids, field_names, arg, context=None):
        # Tinh tong tien ban cho khac hang dua tren so luong va gia tren stock move
        res = {}
        move_obj = self.pool.get('stock.move')
        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.order_line:
                for line in obj.order_line:
                    lst_move = move_obj.search(cr, uid, [('state', '=', 'done'),
                                                         ('picking_id.init_warehouse_id', '!=', False),
                                                         ('sale_id', '=', obj.id),
                                                         ('product_id', '=', line.product_id.id),
                                                         ('location_dest_id.usage', '=', 'customer'),
                                                         ])
                    total += sum([f.product_qty * f.price_unit for f in move_obj.browse(cr, uid, lst_move)])
            res[obj.id] = total
        return res

    def _amount_order(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.order_line:
                total += sum([f.price_order for f in obj.order_line])
            res[obj.id] = total
        return res


    _columns = {
        'customer_order': fields.char('Customer Order', size=256, required=True),
        'lc': fields.char('L/C', size=128),
        'date_send_order': fields.date('Date Send Order'),
        'date_delivery': fields.date('Delivery Date'),
        'usd_rate': fields.float('USD Rate'),

        'amount_order': fields.function(_amount_order, string='Amount Order(USD)', type='float'),

        'amount_real': fields.function(_amount_real, string='Amount Real(USD)(Kg)', type='float',
                                       digits_compute=dp.get_precision('Product Unit of Measure')),
        'total_finish_qty': fields.function(_total_finish_qty, string='Finish Quantity(Kg)', type='float',
                                            digits_compute=dp.get_precision('Product Unit of Measure')),
        'total_qty': fields.function(_total_qty, string='Qty Order(Kg)', type='float',
                                     digits_compute=dp.get_precision('Product Unit of Measure')),
        'total_qty_kg': fields.function(_total_qty_kg, string='Qty Order(Yard)', type='float',
                                        digits_compute=dp.get_precision('Product Unit of Measure')),

        'delivery_qty': fields.function(_delivery_qty, string='Delivery Qty(Kg)', type='float',
                                        digits_compute=dp.get_precision('Product Unit of Measure')),
        'delivery_qty_kg': fields.function(_delivery_qty_kg, string='Delivery Qty(Yard)', type='float',
                                           digits_compute=dp.get_precision('Product Unit of Measure')),
    }


    def copy_quotation(self, cr, uid, ids, context=None):
        name_order = self.browse(cr, uid, ids[0]).name + ' - Cancel'
        self.write(cr, uid, ids[0], {'name': name_order})
        id = self.copy(cr, uid, ids[0], {'name': self.browse(cr, uid, ids[0]).name}, context=None)
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'view_order_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    def edit_sale_order(self, cr, uid, ids, context=None):
        return {'name': 'Edit Sale Order',
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'edit.sale.order.wizard',
                'res_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'context': context,
                'target': 'new',
                'domain': '[]',
                }

    def make_all_cancel(self, cr, uid, ids, context=None):
        # nut cancel don hang
        wf_service = netsvc.LocalService("workflow")
        picking_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        sale_line_obj = self.pool.get('sale.order.line')
        purchase_obj = self.pool.get('purchase.order')
        purchase_line_obj = self.pool.get('purchase.order.line')
        section_obj = self.pool.get('production.section')
        plan_obj = self.pool.get('production.plan')
        plan_sale_obj = self.pool.get('production.plan.sale')
        lst_pick = []
        lst_purchase = []
        for sale in self.browse(cr, uid, ids):
            lst_line = [order_line.id for order_line in sale.order_line]
            lst_line = list(set(lst_line))

            #### section
            lst_section = section_obj.search(cr, uid, [('sale_id', '=', sale.id)])
            section_obj.write(cr, uid, lst_section, {'state': 'cancel'}, context=context)

            #### plan
            lst_plan = plan_obj.search(cr, uid, [('sale_line_id', 'in', lst_line)])
            plan_obj.write(cr, uid, lst_plan, {'state': 'cancel'}, context=context)

            #### sale plan
            lst_sale_plan = plan_sale_obj.search(cr, uid, [('sale_id', '=', sale.id)])
            plan_sale_obj.write(cr, uid, lst_sale_plan, {'state': 'cancel'}, context=context)

            #### picking
            lst_move = move_obj.search(cr, uid, [('sale_line_id', 'in', lst_line)])
            lst_pick = [move.picking_id.id for move in move_obj.browse(cr, uid, lst_move)]
            lst_pick = list(set(lst_pick))
            picking_obj.action_revert_done(cr, uid, lst_pick, context=context)
            picking_obj.write(cr, uid, lst_pick, {'state': 'cancel'})
            move_obj.write(cr, uid, lst_move, {'state': 'cancel'})

            #### purchase
            lst_purchase_line = purchase_line_obj.search(cr, uid, [('sale_line_id', 'in', lst_line)])
            lst_purchase = [line.order_id.id for line in purchase_line_obj.browse(cr, uid, lst_purchase_line)]
            lst_purchase = list(set(lst_purchase))
            for purchase in self.browse(cr, uid, lst_purchase, context=context):
                for pick in purchase.picking_ids:
                    wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
            purchase_obj.write(cr, uid, lst_purchase, {'state': 'cancel'})
            purchase_line_obj.write(cr, uid, lst_purchase_line, {'state': 'cancel'})
            #### sale
            for sale in self.browse(cr, uid, ids, context=context):
                sale_line_obj.write(cr, uid, [l.id for l in sale.order_line],
                                    {'state': 'cancel'})
            self.write(cr, uid, ids, {'state': 'cancel'})

            #### invoice
            lst_invoice_line = invoice_line_obj.search(cr, uid,
                                                       [('sale_id', '=', sale.id), ('invoice_id.state', '=', 'draft')])
            lst_invoice = [line.invoice_id.id for line in invoice_line_obj.browse(cr, uid, lst_invoice_line)]
            lst_invoice = list(set(lst_invoice))
            invoice_obj.unlink(cr, uid, lst_invoice, context=context)

        return True

    def create(self, cr, uid, vals, context=None):
        if not context.get('name', False):
            vals['name'] = vals['customer_order']
        return super(sale_order, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if 'customer_order' in vals:
            vals['name'] = vals['customer_order']
        return super(sale_order, self).write(cr, uid, ids, vals, context=context)

    def _prepare_order_picking(self, cr, uid, order, context=None):
        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        return {
            'name': pick_name,
            'origin': order.name,
            'date': self.date_to_datetime(cr, uid, order.date_order, context),
            'type': 'out',
            'state': 'auto',
            'move_type': order.picking_policy,
            'sale_id': order.id,
            'partner_id': order.partner_shipping_id.id,
            'note': order.note,
            'invoice_state': (order.order_policy == 'picking' and '2binvoiced') or 'none',
            'company_id': order.company_id.id,
            'location_id': order.shop_id.warehouse_id.lot_stock_id.id or False,
        }

    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        location_id = order.shop_id.warehouse_id.lot_stock_id.id
        output_id = order.shop_id.warehouse_id.lot_output_id.id
        return {
            'name': line.name,
            'picking_id': picking_id,
            'product_id': line.product_id.id,
            'date': date_planned,
            'date_expected': date_planned,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id) \
                           or line.product_uom.id,
            'product_packaging': line.product_packaging.id,
            'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
            'location_id': location_id,
            'location_dest_id': output_id,
            'sale_line_id': line.id,
            'tracking_id': False,
            'state': 'draft',
            # 'state': 'waiting',
            'company_id': order.company_id.id,
            'price_unit': line.product_id.standard_price or 0.0,
            'color_id': line.color_id and line.color_id.id or False,
            'qty_kg': line.qty_kg or 0.0,
        }


    def set_to_done_init(self, cr, uid, ids, context=None):
        for o in self.browse(cr, uid, ids, context=context):
            for line in o.order_line:
                self.pool.get('sale.order.line').write(cr, uid, line.id, {'state': 'done'}, context=context)
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)