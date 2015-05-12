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


class production_plan_sale(osv.osv):
    _name = 'production.plan.sale'
    _inherit = ['mail.thread']

    _columns = {
        'name': fields.char('Number', size=256, readonly=True),
        'sale_id': fields.many2one('sale.order', 'Sale Order', required=True, readonly=True,
                                   domain=[('state', '!=', 'cancel')], states={'draft': [('readonly', False)]}),
        'date_create': fields.date('Date Create', readonly=True, states={'draft': [('readonly', False)]}),
        'user_id': fields.many2one('res.users', 'User Create', readonly=True),
        'saleman': fields.many2one('res.users', 'Saleman', readonly=True, states={'draft': [('readonly', False)]}),
        'plan_ids': fields.one2many('production.plan', 'plan_sale_id', 'Plan'),
        'state': fields.selection([('draft', 'Open'),
                                   ('open', 'In Progress'),
                                   ('confirm', 'Plan Sale Confirm'),
                                   ('cancel', 'Cancel'),
                                   ('done', 'Closed')], 'Status'),

    }

    _order = "name desc"

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'production.plan.sale') or ''
        return super(production_plan_sale, self).create(cr, uid, vals, context=context)

    def make_cancel(self, cr, uid, ids, context=None):
        plan_obj = self.pool.get('production.plan')
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        section_obj = self.pool.get('production.section')
        for sale_plan_obj in self.browse(cr, uid, ids):
            if sale_plan_obj.plan_ids:
                for plan in sale_plan_obj.plan_ids:
                    if plan.section_ids:
                        for section in plan.section_ids:
                            lst_move = move_obj.search(cr, uid, [('section_id', '=', section.id)])
                            move_obj.write(cr, uid, lst_move, {'state': 'cancel'}, context)

                            lst_move = move_obj.search(cr, uid, [('section_id', '=', section.id)])
                            lst_pick = [move.picking_id.id for move in move_obj.browse(cr, uid, lst_move)]
                            lst_pick = list(set(lst_pick))
                            picking_obj.action_revert_done(cr, uid, lst_pick, context=context)
                            picking_obj.write(cr, uid, lst_pick, {'state': 'cancel'})
                            move_obj.write(cr, uid, lst_move, {'state': 'cancel'})


                            section_obj.write(cr, uid, section.id, {'state': 'cancel'}, context)
                    plan_obj.write(cr, uid, plan.id, {'state': 'cancel'}, context)
        return self.write(cr, uid, ids, {'state': 'cancel'}, context)

    def sale_change(self, cr, uid, ids, sale_id, context=None):
        if not sale_id:
            return {}
        result = {'value': {}}
        sale = self.pool.get('sale.order').browse(cr, uid, sale_id) or False
        if sale:
            result['value'].update({
                'saleman': sale.user_id and sale.user_id.id or False,
            })
        return result

    def make_plan_line(self, cr, uid, ids, context=None):
        sale_id = self.browse(cr, uid, ids)[0].sale_id.id
        return {'name': 'Define Plan Line',
                'view_mode': 'tree,form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'production.plan',
                'res_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'context': {'plan_sale_id': ids[0], 'default_plan_sale_id': ids[0], 'sale_id': sale_id},
                'domain': [('plan_sale_id', '=', ids[0])],
        }


    _defaults = {
        'state': lambda *a: 'draft',
        'user_id': lambda self, cr, uid, context: uid,
        'date_create': lambda *a: datetime.now().strftime('%Y-%m-%d'),
    }
