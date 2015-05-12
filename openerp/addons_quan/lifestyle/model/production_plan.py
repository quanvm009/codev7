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
from datetime import datetime

from openerp.osv import osv
from openerp.osv import fields
import openerp.addons.decimal_precision as dp


class production_plan(osv.osv):
    _name = 'production.plan'
    _inherit = ['mail.thread']

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        """
            Add domain 'allow_check_writing = True' on journal_id field and remove 'widget = selection' on the same
            field because the dynamic domain is not allowed on such widget
        """
        if not context: context = {}
        res = super(production_plan, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                           context=context, toolbar=toolbar, submenu=submenu)
        fields = res.get('fields', {})
        if fields:
            if fields.get('sale_line_id') and context.get('sale_id', False):
                line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', context['sale_id']),
                                                                             ('order_id.state', 'not in',
                                                                              ('cancel', 'draft', 'done'))])
                res['fields']['sale_line_id']['domain'] = [('id', 'in', line_ids)]
        return res

    _columns = {
        'name': fields.char('Number', size=256, readonly=True),
        'sale_line_id': fields.many2one('sale.order.line', 'Sale Order Line', required=True, readonly=True,
                                        states={'draft': [('readonly', False)]},
                                        domain=[('order_id.state', 'not in', ('cancel', 'draft', 'done'))]),
        'sale_id': fields.related('sale_line_id', 'order_id', type='many2one', readonly=True, relation='sale.order',
                                  string='Sale Order', store={
                _name: (lambda self, cr, uid, ids, c: ids, ['sale_line_id'], 10)
            }),
        'partner_id': fields.related('sale_id', 'partner_id', type='many2one', readonly=True, relation='res.partner',
                                     string='Customer'),
        'lc': fields.related('sale_id', 'lc', type='char', size=64, string='L/C', readonly=True),
        'date_create': fields.date('Date Create', readonly=True, states={'draft': [('readonly', False)]}),
        'user_id': fields.many2one('res.users', 'User Create', readonly=True),
        'saleman': fields.related('sale_id', 'user_id', type='many2one', readonly=True, relation='res.users',
                                  string='Saleman'),
        'product_id': fields.many2one('product.product', 'Product', readonly=True,
                                      states={'draft': [('readonly', False)]}),
        'quantity': fields.float('Qty(Kg)', digits_compute=dp.get_precision('Product Unit of Measure'), required=True,
                                 readonly=True, states={'draft': [('readonly', False)]}),
        'qty_kg': fields.float('Qty(Yard)', digits_compute=dp.get_precision('Product Unit of Measure'), required=True,
                               readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'UoM', readonly=True, states={'draft': [('readonly', False)]}),
        'section_ids': fields.one2many('production.section', 'plan_id', 'Section'),
        'state': fields.selection([('draft', 'Open'),
                                   ('open', 'In Progress'),
                                   ('confirm', 'Section Confirm'),
                                   ('cancel', 'Cancel'),
                                   ('done', 'Closed')], 'Status'),
        'history_ids': fields.one2many('history.plan', 'plan_id', 'History', readonly=True),
        'plan_sale_id': fields.many2one('production.plan.sale', 'Plan Sale'),
    }

    _order = "name desc"

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'production.plan') or ''
        return super(production_plan, self).create(cr, uid, vals, context=context)

    def make_po(self, cr, uid, ids, context=None):
        return {'name': 'Infor Section',
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'create.po.wizard',
                'res_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'context': context,
                'target': 'new',
                'domain': '[]',
        }

    def make_section(self, cr, uid, ids, context=None):
        return {'name': 'Define Section',
                'view_mode': 'form,tree',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'production.section',
                'res_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'context': {'plan_id': ids[0], 'default_plan_id': ids[0]},
                'domain': [('plan_id', '=', ids[0])],
        }


    def make_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context)

    def make_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancel'}, context)

    def make_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context)

    def make_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'open'}, context)

    def action_confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'confirm'}, context)

    def sale_line_change(self, cr, uid, ids, sale_line_id, context=None):
        if not sale_line_id:
            return {}
        result = {'value': {}}
        sale_line = self.pool.get('sale.order.line').browse(cr, uid, sale_line_id) or False
        if sale_line:
            result['value'].update({'product_id': sale_line.product_id and sale_line.product_id.id or False,
                                    'quantity': sale_line.product_uom_qty or 0,
                                    'qty_kg': sale_line.qty_kg or 0,
                                    'product_uom': sale_line.product_id and (
                                        sale_line.product_id.uom_id and sale_line.product_id.uom_id.id or False) or False,
                                    'saleman': sale_line.order_id.user_id and sale_line.order_id.user_id.id or False,
                                    'sale_id': sale_line.order_id and sale_line.order_id.id or False,
                                    'partner_id': sale_line.order_id.partner_id and sale_line.order_id.partner_id.id or False,
                                    'lc': sale_line.order_id.lc or '',
            })
        return result

    _defaults = {
        'state': lambda *a: 'draft',
        'user_id': lambda self, cr, uid, context: uid,
        'date_create': lambda *a: datetime.now().strftime('%Y-%m-%d'),
    }


class history_plan(osv.osv):
    _name = "history.plan"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'quantity': fields.float('Qty(Kg)'),
        'qty_kg': fields.float('Qty(Yard)'),
        'user_id': fields.many2one('res.users', 'User Create'),
        'date_create': fields.date('Date Create'),
        'plan_id': fields.many2one('production.plan', 'Plan'),
    }
    _defaults = {
    }    
