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
from openerp.osv import osv
from openerp.osv import fields
from openerp import netsvc
import openerp.addons.decimal_precision as dp


class sale_order_line(osv.osv):

    def name_get(self, cr, user, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = self.browse(cr, user, ids, context=context)
        res = []
        for rs in result:
            id_temp = rs.id or False
            name = '''[%s] [%s]%s %s''' % (
                rs.order_id and rs.order_id.name or '', rs.categ_id and rs.categ_id.name or '', rs.product_id.name,
                rs.color_id and rs.color_id.name or '')
            res += [(id_temp, name)]
        return res

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        ids = []
        if ids:
            ids = self.search(cr, user, [('name', '=', name)] + args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('order_id.name', operator, name)] + args, limit=limit)
        return self.name_get(cr, user, ids, context)

    def _amount_line_kg(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit_kg * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.qty_kg, line.product_id,
                                        line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res


    _inherit = 'sale.order.line'
    _columns = {
        'order_id': fields.many2one('sale.order', 'Order Reference'),
        'code': fields.char('Code Product'),
        'weight_prod': fields.char('Weight'),
        'width': fields.char('Width'),
        'color_id': fields.many2one('product.color', 'Color'),
        'categ_id': fields.many2one('product.category', 'Product Code'),
        'qty_kg': fields.float('Qty(Yard)'),
        'price_unit_kg': fields.float('Unit Price(Yard)'),
        'price_subtotal_kg': fields.function(_amount_line_kg, string='Subtotal (Yard)',
                                             digits_compute=dp.get_precision('Account')),
        'product_id': fields.many2one('product.product', 'Product',
                                      domain="[('sale_ok', '=', True),('categ_id', '=', categ_id)]",
                                      change_default=True),
        'price_order': fields.float('Amount Order(USD)(Kg)'),
        'price_order_kg': fields.float('Amount Order(USD)(Yard)'),

        'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price')),
        'product_uom_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product UoS'), required=True),
    }

    def invoice_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        create_ids = []
        sales = set()
        for line in self.browse(cr, uid, ids, context=context):
            vals = self._prepare_order_line_invoice_line(cr, uid, line, False, context)
            vals['sale_id'] = line.order_id.id
            vals['qty_kg'] = line.qty_kg
            if vals:
                inv_id = self.pool.get('account.invoice.line').create(cr, uid, vals, context=context)
                self.write(cr, uid, [line.id], {'invoice_lines': [(4, inv_id)]}, context=context)
                sales.add(line.order_id.id)
                create_ids.append(inv_id)
        # Trigger workflow events
        wf_service = netsvc.LocalService("workflow")
        for sale_id in sales:
            wf_service.trg_write(uid, 'sale.order', sale_id, cr)
        return create_ids
