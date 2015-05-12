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



from openerp import netsvc
from openerp.osv import fields
from openerp.osv import osv

import openerp.addons.decimal_precision as dp


class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'sale_line_id': fields.many2one('sale.order.line', 'Sales Order Line', ondelete='set null', select=True),
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True,
                                      domain=[('type', '<>', 'service')]),
        'sale_id': fields.related('picking_id', 'sale_id', type='many2one', relation='sale.order', store=True,
                                  string='Sale'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
                                    required=True),
        'section_id': fields.many2one('production.section', 'Section'),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line'),
        'color_id': fields.many2one('product.color', 'Color', required=False),
        'lot': fields.char('Lot', size=256),
        'roll': fields.char('Roll', size=256),
        'weight': fields.char('Weight', size=256),
        'width': fields.char('Width', size=256),
        'address': fields.char('Address', szie=256),
        'qty_kg': fields.float('Qty(Yard)'),
        'qty_kg_real': fields.float('Qty(Kgs) Order'),
        'qty_yrd_real': fields.float('Qty(Yrd) Order'),
        'processing_price': fields.float('Processing Price'),
        'user_id': fields.many2one('res.users', 'User'),
    }

    _defaults = {
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def write(self, cr, uid, ids, vals, context=None):
        result = super(stock_move, self).write(cr, uid, ids, vals, context)
        history_factory_detail_obj = self.pool.get('history.factory.detail')
        for obj in self.browse(cr, uid, ids, context=context):
            history_detail_id = history_factory_detail_obj.search(cr, uid, [('move_id', '=', obj.id)], context=context)
            if history_detail_id and history_detail_id[0]:
                if vals.get('product_qty'):
                    history_factory_detail_obj.write(cr, uid, history_detail_id[0],
                                                     {'quantity': vals.get('product_qty')},
                                                     context=context)


        return result

    def action_done(self, cr, uid, ids, context=None):
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id.type == 'in':
                break
            new_ctx = {'uom': move.product_uom.id}
            # if move.color_id:
            # new_ctx.update({'color_id': move.color_id.id})
            if move.sale_line_id:
                new_ctx.update({'sale_line_id': move.sale_line_id.id})
            check = self.pool.get('stock.location')._product_reserve(cr, uid, [move.location_id.id], move.product_id.id,
                                                                     move.product_qty, new_ctx, lock=True)
            # INIT-quan
            # if not check:
            #     raise osv.except_osv(_('Error!'),
            #                          _('Not enough quantity.'))
        return super(stock_move, self).action_done(cr, uid, ids, context)

    def check_assign(self, cr, uid, ids, context=None):
        """ Checks the product type and accordingly writes the state.
        @return: No. of moves done
        """
        done = []
        count = 0
        pickings = {}
        if context is None:
            context = {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.product_id.type == 'consu' or move.location_id.usage == 'supplier':
                if move.state in ('confirmed', 'waiting'):
                    done.append(move.id)
                pickings[move.picking_id.id] = 1
                continue

            if move.state in ('confirmed', 'waiting'):
                # Important: we must pass lock=True to _product_reserve() to avoid race conditions and double reservations
                new_ctx = {'uom': move.product_uom.id}

                if move.color_id:
                    new_ctx.update({'color_id': move.color_id.id})
                if move.sale_line_id:
                    new_ctx.update({'sale_line_id': move.sale_line_id.id})

                res = self.pool.get('stock.location')._product_reserve(cr, uid, [move.location_id.id],
                                                                       move.product_id.id, move.product_qty, new_ctx,
                                                                       lock=True)
                if res:
                    # _product_available_test depends on the next status for correct functioning
                    # the test does not work correctly if the same product occurs multiple times
                    # in the same order. This is e.g. the case when using the button 'split in two' of
                    # the stock outgoing form
                    self.write(cr, uid, [move.id], {'state': 'assigned'})
                    done.append(move.id)
                    pickings[move.picking_id.id] = 1
                    r = res.pop(0)
                    product_uos_qty = \
                        self.pool.get('stock.move').onchange_quantity(cr, uid, ids, move.product_id.id, r[0],
                                                                      move.product_id.uom_id.id,
                                                                      move.product_id.uos_id.id)[
                            'value']['product_uos_qty']
                    cr.execute('update stock_move set location_id=%s, product_qty=%s, product_uos_qty=%s where id=%s',
                               (r[1], r[0], product_uos_qty, move.id))

                    while res:
                        r = res.pop(0)
                        product_uos_qty = \
                            self.pool.get('stock.move').onchange_quantity(cr, uid, ids, move.product_id.id, r[0],
                                                                          move.product_id.uom_id.id,
                                                                          move.product_id.uos_id.id)['value'][
                                'product_uos_qty']
                        move_id = self.copy(cr, uid, move.id, {'product_uos_qty': product_uos_qty, 'product_qty': r[0],
                                                               'location_id': r[1]})
                        done.append(move_id)
        if done:
            count += len(done)
            self.write(cr, uid, done, {'state': 'assigned'})

        if count:
            for pick_id in pickings:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_write(uid, 'stock.picking', pick_id, cr)
        return count

    def set_to_draft_init(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def set_to_done_init(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def split_move(self, cr, uid, ids, context=None):
        return {'name': 'Split Move',
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'split.move.wizard',
                'res_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'context': context,
                'target': 'new',
                'domain': '[]',
        }
