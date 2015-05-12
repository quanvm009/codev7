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

import time

from dateutil.relativedelta import relativedelta
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.float_utils import float_is_zero
from openerp.tools.translate import _
from openerp import netsvc


class split_move_wizard(osv.osv_memory):
    _name = "split.move.wizard"

    def default_get(self, cr, uid, fields, context):
        if context is None:
            context = {}
        res = super(split_move_wizard, self).default_get(cr, uid, fields, context=context)

        obj_move = self.pool.get('stock.move').browse(cr, uid, context['active_ids'])
        if obj_move and obj_move[0]:
            move = obj_move[0]
            res.update({
                'color_id': move.color_id and move.color_id.id or False,
                'lot': move.lot or '',
                'roll': move.roll or '',
                'weight': move.weight or '',
                'width': move.width or '',
                'address': move.address or '',
                'note': move.note or '',

                'qty_kg_real': move.qty_kg_real or 0,
                'qty_yrd_real': move.qty_yrd_real or 0,
                'price_unit': move.price_unit or 0,
                'processing_price': move.processing_price or 0,
            })
        return res

    _columns = {
        'color_id': fields.many2one('product.color', 'Color', required=False),
        'lot': fields.char('Lot', size=256),
        'roll': fields.char('Roll', size=256),
        'weight': fields.char('Weight', szie=256),
        'width': fields.char('Width', szie=256),
        'address': fields.char('Address', szie=256),
        'note': fields.text('Notes'),
        'product_qty': fields.float('Qty(Kg)'),
        'qty_kg': fields.float('Qty(Yard)'),
        'qty_kg_real': fields.float('Qty(Kgs) Order'),
        'qty_yrd_real': fields.float('Qty(Yrd) Order'),
        'price_unit': fields.float('Price Unit'),
        'processing_price': fields.float('Processing Price'),


        'note': fields.text('Notes'),
    }

    _defaults = {
    }

    def make_split_move(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        rec_id = context and context.get('active_ids', False)
        move_obj = self.pool.get('stock.move')
        quantity = self.browse(cr, uid, ids[0], context=context).product_qty or 0.0  #### so luong tren form con
        qty_kg = self.browse(cr, uid, ids[0], context=context).qty_kg or 0.0
        obj = self.browse(cr, uid, ids[0], context=context)

        for move in move_obj.browse(cr, uid, rec_id, context=context):
            quantity_rest = move.product_qty - quantity  ####  sl du
            if quantity > move.product_qty:
                raise osv.except_osv(_('Error!'), _('Total quantity after split exceeds the quantity to split ' \
                                                    'for this product: "%s" (id: %d).') % \
                                     (move.product_id.name, move.product_id.id,))
            if quantity > 0:
                #                 move_obj.setlast_tracking(cr, uid, [move.id], context=context)
                move_obj.write(cr, uid, [move.id], {
                    'product_qty': quantity_rest,
                    'qty_kg': move.qty_kg - qty_kg or 0,
                })

            if quantity_rest >= 0:
                quantity_rest = move.product_qty - quantity
                default_val = {
                    'product_qty': quantity,
                    'qty_kg': obj.qty_kg or 0,
                    'qty_kg_real': obj.qty_kg_real or 0,
                    'qty_yrd_real': obj.qty_yrd_real or 0,
                    'state': move.state,
                    'color_id': obj.color_id and obj.color_id.id or False,
                    'lot': obj.lot or '',
                    'roll': obj.roll or '',
                    'weight': obj.weight or '',
                    'width': obj.width or '',
                    'address': obj.address or '',
                    'note': obj.note or '',
                    'price_unit': obj.price_unit or 0,
                    'processing_price': obj.processing_price or 0,
                }
                current_move = move_obj.copy(cr, uid, move.id, default_val, context=context)
        return {'type': 'ir.actions.act_window_close'}


split_move_wizard()



