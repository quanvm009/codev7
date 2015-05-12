# -*- coding: utf-8 -*-
# #############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 INIT TECH (<http://init.vn>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#'product_id': fields.related('order_line','product_id', type='many2one', relation='product.product', string='Product'),
##############################################################################

from openerp.osv import fields, osv


class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'sale_id': fields.related('invoice_line', 'sale_id', type='many2one', relation='sale.order',
                                  string='Sale Order'),
    }


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
        'sale_id': fields.many2one('sale.order', 'Sale Order'),
        'wf_create': fields.boolean('Not Manual'),
        'qty_kg': fields.float('Qty(Yard)'),
    }