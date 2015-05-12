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


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'code': fields.char('Code', size=256),
    }

    def create(self, cr, uid, vals, context=None):
        if 'customer' in vals and vals['customer'] == True:
            vals['code'] = self.pool.get('ir.sequence').get(cr, uid, 'res.partner') or '/'
        else:
            vals['code'] = self.pool.get('ir.sequence').get(cr, uid, 'res.partner.cus') or '/'
        return super(res_partner, self).create(cr, uid, vals, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
