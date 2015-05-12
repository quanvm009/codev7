# -*- coding: utf-8 -*-
# #############################################################################
#
#    INIT TECH, Open Source Management Solution
#    Copyright (C) 2012-2013 Tiny SPRL (<http://init.vn>).
#
##############################################################################
from openerp.osv import fields, osv
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import time
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_compare


class stock_partial_picking_line(osv.osv_memory):
    _inherit = "stock.partial.picking.line"
    _columns = {
        'color_id': fields.many2one('product.color', 'Color'),
        'qty_kg': fields.float('Qty(Yard)'),
        'lot': fields.char('Lot', size=256),
        'roll': fields.char('Roll', size=256),
        'note': fields.text('Notes'),
        'width': fields.char('Width', size=256),
        'weight': fields.char('Weight', size=256),

        'price_unit': fields.float('Price Unit'),
        'processing_price': fields.float('Processing Price'),
        'qty_kg': fields.float('Qty(Yard)'),
        'qty_kg_real': fields.float('Qty(Kgs) Order'),
        'qty_yrd_real': fields.float('Qty(Yrd) Order'),
    }


class stock_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"


    def _partial_move_for(self, cr, uid, move):
        partial_move = {
            'color_id': move.color_id and move.color_id.id or False,
            'qty_kg': move.qty_kg or 0,
            'width': move.width or '',
            'weight': move.weight or '',
            'note': move.note or '',
            'lot': move.lot or '',
            'roll': move.roll or '',
            'qty_kg_real': move.qty_kg_real or 0,
            'qty_yrd_real': move.qty_yrd_real or 0,
            'price_unit': move.price_unit or 0,
            'processing_price': move.processing_price or 0,

            'product_id': move.product_id.id,
            'quantity': move.product_qty if move.state == 'assigned' or move.picking_id.type == 'in' else 0,
            'product_uom': move.product_uom.id,
            'prodlot_id': move.prodlot_id.id,
            'move_id': move.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
        }
        if move.picking_id.type == 'in' and move.product_id.cost_method == 'average':
            partial_move.update(update_cost=True, **self._product_cost_for_average_update(cr, uid, move))
        return partial_move

    def do_partial(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'Partial picking processing may only be done one at a time.'
        stock_picking = self.pool.get('stock.picking')
        stock_move = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date': partial.date
        }
        picking_type = partial.picking_id.type
        for wizard_line in partial.move_ids:
            line_uom = wizard_line.product_uom
            move_id = wizard_line.move_id.id

            # Quantiny must be Positive
            if wizard_line.quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Please provide proper Quantity.'))

            # Compute the quantity for respective wizard_line in the line uom (this jsut do the rounding if necessary)
            qty_in_line_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, line_uom.id)

            if line_uom.factor and line_uom.factor <> 0:
                if float_compare(qty_in_line_uom, wizard_line.quantity, precision_rounding=line_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _(
                        'The unit of measure rounding does not allow you to ship "%s %s", only rounding of "%s %s" is accepted by the Unit of Measure.') % (
                                         wizard_line.quantity, line_uom.name, line_uom.rounding, line_uom.name))
            if move_id:
                # Check rounding Quantity.ex.
                # picking: 1kg, uom kg rounding = 0.01 (rounding to 10g),
                # partial delivery: 253g
                # => result= refused, as the qty left on picking would be 0.747kg and only 0.75 is accepted by the uom.
                initial_uom = wizard_line.move_id.product_uom
                # Compute the quantity for respective wizard_line in the initial uom
                qty_in_initial_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, initial_uom.id)
                without_rounding_qty = (wizard_line.quantity / line_uom.factor) * initial_uom.factor
                if float_compare(qty_in_initial_uom, without_rounding_qty,
                                 precision_rounding=initial_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _(
                        'The rounding of the initial uom does not allow you to ship "%s %s", as it would let a quantity of "%s %s" to ship and only rounding of "%s %s" is accepted by the uom.') % (
                                         wizard_line.quantity, line_uom.name,
                                         wizard_line.move_id.product_qty - without_rounding_qty, initial_uom.name,
                                         initial_uom.rounding, initial_uom.name))
            else:
                seq_obj_name = 'stock.picking.' + picking_type
                move_id = stock_move.create(cr, uid, {'name': self.pool.get('ir.sequence').get(cr, uid, seq_obj_name),
                                                      'product_id': wizard_line.product_id.id,
                                                      'product_qty': wizard_line.quantity,
                                                      'product_uom': wizard_line.product_uom.id,
                                                      'prodlot_id': wizard_line.prodlot_id.id,
                                                      'location_id': wizard_line.location_id.id,
                                                      'location_dest_id': wizard_line.location_dest_id.id,
                                                      'color_id': wizard_line.color_id and wizard_line.color_id.id or False,
                                                      'qty_kg': wizard_line.qty_kg or 0,
                                                      'width': wizard_line.width or '',
                                                      'weight': wizard_line.weight or '',
                                                      'note': wizard_line.note or '',
                                                      'qty_kg_real': wizard_line.qty_kg_real or 0,
                                                      'qty_yrd_real': wizard_line.qty_yrd_real or 0,
                                                      'price_unit': wizard_line.price_unit or 0,
                                                      'processing_price': wizard_line.processing_price or 0,
                                                      'picking_id': partial.picking_id.id
                }, context=context)
                stock_move.action_confirm(cr, uid, [move_id], context)

            # check inventory again
            stock_move.check_assign(cr, uid, [move_id], context)

            partial_data['move%s' % (move_id)] = {
                'product_id': wizard_line.product_id.id,
                'product_qty': wizard_line.quantity,
                'product_uom': wizard_line.product_uom.id,
                'prodlot_id': wizard_line.prodlot_id.id,

                'color_id': wizard_line.color_id and wizard_line.color_id.id,
                'qty_kg': wizard_line.qty_kg,
                'lot': wizard_line.lot,
                'roll': wizard_line.roll,
                'width': wizard_line.width,
                'weight': wizard_line.weight,
                'note': wizard_line.note,
                'qty_kg_real': wizard_line.qty_kg_real,
                'qty_yrd_real': wizard_line.qty_yrd_real,
                'price_unit': wizard_line.price_unit or 0,
                'processing_price': wizard_line.processing_price or 0,
            }
            if (picking_type == 'in') and (wizard_line.product_id.cost_method == 'average'):
                partial_data['move%s' % (wizard_line.move_id.id)].update(product_price=wizard_line.cost,
                                                                         product_currency=wizard_line.currency.id)

        stock_picking.do_partial(cr, uid, [partial.picking_id.id], partial_data, context=context)
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
