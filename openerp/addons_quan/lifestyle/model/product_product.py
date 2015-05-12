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


class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'weight_prod': fields.char('Weight', size=256, required=False),
        'width': fields.char('Width', size=256, required=False),
        'color_id': fields.many2one('product.color', 'Color', required=False),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Order Reference must be unique per Company!'),
    ]


class product_category(osv.osv):
    _inherit = 'product.category'
    _columns = {
        'finish': fields.boolean('Finish Product'),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
