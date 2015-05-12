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
from openerp.osv import osv
from openerp.osv import fields
from openerp import netsvc
from operator import itemgetter


class purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def _get_sale_id(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for rec in self.browse(cr, uid, ids, context=context):
            result[rec.id] = (rec.order_line and (
            rec.order_line[0].sale_line_id and rec.order_line[0].sale_line_id.order_id.id or False) or False,
                              rec.order_line and (rec.order_line[0].sale_line_id and rec.order_line[
                                  0].sale_line_id.order_id.name or False) or False)
        return result

    def _sale_search(self, cr, uid, obj, name, args, domain=None, context=None):
        having_values = map(itemgetter(2), args)
        pol_obj = self.pool.get('purchase.order.line')
        list_pol = pol_obj.search(cr, uid, [('sale_line_id.order_id.id', 'in', having_values)])
        list_po = [pol.order_id.id for pol in pol_obj.browse(cr, uid, list_pol)]
        list_po = list(set(list_po))
        return [('id', 'in', list_po)]

    _columns = {
        'sale_id': fields.function(_get_sale_id, type='many2one', fnct_search=_sale_search, relation='sale.order',
                                   string='Sale Order'),
        'partner_cus': fields.related('sale_id', 'partner_id', type='many2one', relation='res.partner',
                                      string='Customer', store=True, readonly=True),
        'saleman': fields.related('sale_id', 'user_id', type='many2one', relation='res.users', string='Saleman',
                                  store=True, readonly=True),
        'lc': fields.related('sale_id', 'lc', type='char', string='LC', readonly=True),
        'user_id': fields.many2one('res.users', 'User'),
    }

    _defaults = {
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, context=None):
        return {
            'name': order_line.name or '',
            'product_id': order_line.product_id.id,
            'product_qty': order_line.product_qty,
            'product_uos_qty': order_line.product_qty,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'date': self.date_to_datetime(cr, uid, order.date_order, context),
            'date_expected': self.date_to_datetime(cr, uid, order_line.date_planned, context),
            'location_id': order.partner_id.property_stock_supplier.id,
            'location_dest_id': order.location_id.id,
            'picking_id': picking_id,
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'move_dest_id': order_line.move_dest_id.id,
            'state': 'draft',
            'type': 'in',
            'purchase_line_id': order_line.id,
            'company_id': order.company_id.id,
            'price_unit': order_line.price_unit,
            'sale_line_id': order_line.sale_line_id.id and order_line.sale_line_id.id or False,
            'qty_kg': order_line.qty_kg or 0.0
        }


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'
    _columns = {
        'sale_line_id': fields.many2one('sale.order.line', 'Sale Line', ),
        'qty_kg': fields.float('Qty(Yard)'),
    }
