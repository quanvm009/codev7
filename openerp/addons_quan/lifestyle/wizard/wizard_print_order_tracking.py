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


class wizard_print_order_tracking(osv.osv_memory):
    _name = 'wizard.print.order.tracking'
    _columns = {
        'sale_id': fields.many2one('sale.order', 'Sale Order', required=True),
        'stock_id': fields.many2one('stock.warehouse', 'Factory', required=True)
    }

    def onchange_sale_id(self, cr, uid, ids, sale_id, context=None):
        if context is None:
            context = {}
        res = {'value': {}}
        line_obj = self.pool.get('sale.order.line')
        plan_obj = self.pool.get('production.plan')
        section_obj = self.pool.get('production.section')
        if sale_id:
            line_ids = line_obj.search(cr, uid, [('order_id', '=', sale_id)])
        stock_ids = []
        for line in line_ids:
            plan_ids = plan_obj.search(cr, uid, [('sale_line_id', '=', line)])
            if plan_ids:
                section_ids = section_obj.search(cr, uid, [('plan_id', '=', plan_ids)])
                if section_ids:
                    id_old = 0
                    for section in section_obj.browse(cr, uid, section_ids):
                        if id_old != section.stock_id.id:
                            id_old = section.stock_id.id
                            stock_ids.append(section.stock_id.id)
        return {'domain': {'stock_id': [('id', 'in', stock_ids)]}}

    def print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = {'ids': context.get('active_ids', []), 'form': self.read(cr, uid, ids)[0]}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'order_tracking_report',
            'datas': data,
            'name': 'Order Tracking Report',
        }
