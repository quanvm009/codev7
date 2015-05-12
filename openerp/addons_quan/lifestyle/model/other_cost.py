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
#
##############################################################################

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class other_cost(osv.osv):
    _name = 'other.cost'
    _description = 'Other Cost'

    def _get_price_subtotal(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            val = 0.0
            for move in line.cost_ids:
                val += move.price_total
            res[line.id] = val
        return res

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'sale_id': fields.many2one('sale.order', 'Sale Order', required=True),
        'cost_ids': fields.one2many('other.cost.line', 'cost_id', 'Costs'),
        'price_subtotal': fields.function(_get_price_subtotal, method=True, string='Sub Total'),
    }


class other_cost_line(osv.osv):
    _name = 'other.cost.line'
    _description = 'Other Cost Line'

    def _get_price_total(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            val = 0.0
            val = line.price_unit * line.quantity
            res[line.id] = val
        return res

    _columns = {
        'cost_id': fields.many2one('other.cost', 'Cost'),
        'name': fields.char('Name', size=256),
        'quantity': fields.float('Quantity'),
        'price_unit': fields.float('Unit Price', digits_compute=dp.get_precision('Product Price')),
        'price_total': fields.function(_get_price_total, method=True, string='Total'),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
