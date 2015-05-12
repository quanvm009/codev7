# -*- coding: utf-8 -*-
# #############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv


class invoice_factory_wizard(osv.osv_memory):
    _name = 'invoice.factory.wizard'
    _description = 'Invoice Factory Wizard'
    _columns = {
        'sale_id': fields.many2one('sale.order', string='Sale Order', domain=[('state', '!=', 'cancel')],
                                   required=True),
        'section_id': fields.many2one('production.section', string='Section', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', string='Factory', required=True),
        'date': fields.date('Date', required=True),
    }

    def onchange_sale_id(self, cr, uid, ids, sale_id, context=None):
        if context is None:
            context = {}
        line_obj = self.pool.get('sale.order.line')
        plan_obj = self.pool.get('production.plan')
        section_obj = self.pool.get('production.section')
        if sale_id:
            line_ids = line_obj.search(cr, uid, [('order_id', '=', sale_id)])
        for line in line_ids:
            plan_ids = plan_obj.search(cr, uid, [('sale_line_id', '=', line)])
            if plan_ids:
                section_ids = section_obj.search(cr, uid, [('plan_id', '=', plan_ids)])
        return {'domain': {'section_id': [('id', 'in', section_ids)]}}

    def onchange_section_id(self, cr, uid, ids, section_id, context=None):
        if context is None:
            context = {}
        section_obj = self.pool.get('production.section')
        warehouse_ids = []
        if section_id:
            for line in section_obj.browse(cr, uid, section_id).history_fact_ids:
                warehouse_ids.append(line.stock_id.id)
        return {'domain': {'warehouse_id': [('id', 'in', warehouse_ids)]}}

    def make_invoice(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        journal_obj = self.pool.get('account.journal')
        invoice_line_obj = self.pool.get('account.invoice.line')
        picking_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        group = False
        for obj in self.browse(cr, uid, ids):
            date = obj.date or ''
            section_id = obj.section_id
            warehouse_id = obj.warehouse_id
            partner = obj.warehouse_id.partner_id
            list_move = move_obj.search(cr, uid, [('section_id', '=', section_id.id),
                                                  ('state', '=', 'done'),
                                                  ('picking_id.invoice_state', '=', '2binvoiced'),
                                                  ('location_dest_id', '=', warehouse_id.lot_stock_id.id)])
            if list_move:
                vals = []
                value = journal_obj.search(cr, uid, [('type', '=', 'purchase')])
                for jr_type in journal_obj.browse(cr, uid, value, context=context):
                    t1 = jr_type.id
                    if t1 not in vals:
                        vals.append(t1)
                inv_data = {
                    'type': 'in_invoice',
                    'account_id': partner.property_account_payable.id,
                    'partner_id': partner.id,
                    'payment_term': partner.property_payment_term.id or False,
                    'date_invoice': date,
                    'user_id': uid,
                    'fiscal_position': partner.property_account_position.id,
                    'journal_id': vals[0],
                }

                inv_id = invoice_obj.create(cr, uid, inv_data, context=context)
                pick_ids = []

                for move in move_obj.browse(cr, uid, list_move):
                    pick_ids.append(move.picking_id.id)
                    value = picking_obj._prepare_invoice_line(cr, uid, group, move.picking_id,
                                                              move, inv_id, inv_data, context=context)
                    if value:
                        value.update({'sale_id': move.sale_line_id.order_id.id,
                                      'uos_id': move.product_uom.id,
                                      'qty_kg': move.qty_kg or 0})
                        invoice_line_id = invoice_line_obj.create(cr, uid, value, context=context)
                        move_obj.write(cr, uid, move.id, {'invoice_line_id': invoice_line_id}, context=context)
                pick_ids = list(set(pick_ids))
                picking_obj.write(cr, uid, pick_ids, {'invoice_state': 'invoiced'}, context=context)
        return True


invoice_factory_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
