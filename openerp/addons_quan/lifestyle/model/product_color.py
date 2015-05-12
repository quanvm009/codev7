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


class product_color(osv.osv):
    _name = 'product.color'
    _description = 'Color Of Product'
    _columns = {
        'name': fields.char('Name', size=64, required=False, readonly=False),
        'code': fields.char('Code', size=64, required=False, readonly=False),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
