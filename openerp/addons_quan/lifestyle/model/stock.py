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
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
from openerp import netsvc


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _get_section(self, cr, uid, ids, field_names, arg, context=None):
        res = {}

        for obj in self.browse(cr, uid, ids):
            name = 0
            for move in obj.move_lines:
                if move.section_id:
                    name = '%s, %s' % (name, move.section_id.name)
            res[obj.id] = name
        return res

    _columns = {
        'date_done': fields.datetime('Date of Transfer'),
        'section_id': fields.many2one('production.section', 'Section',
                                      states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'plan_name': fields.function(_get_section, string='Plan', type='char'),
        'init_warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',
                                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'internal_id': fields.many2one('internal.order', 'Internal Order'),
        'sale_line_id': fields.related('move_lines', 'sale_line_id', type='many2one', relation='sale.order.line',
                                       string='Sale'),
        'user_id': fields.many2one('res.users', 'User'),
    }

    _defaults = {
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def _get_invoice_type(self, pick):
        src_usage = dest_usage = None
        inv_type = None
        if pick.invoice_state == '2binvoiced':
            if pick.move_lines:
                src_usage = pick.move_lines[0].location_id.usage
                dest_usage = pick.move_lines[0].location_dest_id.usage
            if pick.type == 'out' and dest_usage == 'supplier':
                inv_type = 'in_refund'
            elif pick.type == 'out' and dest_usage == 'customer':
                inv_type = 'out_invoice'
            elif pick.type == 'in' and src_usage in ('supplier', 'production'):
                inv_type = 'in_invoice'
            elif pick.type == 'in' and src_usage == 'customer':
                inv_type = 'out_refund'
            else:
                inv_type = 'out_invoice'
        return inv_type

    def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):
        return move_line.price_unit

    def action_invoice_create(self, cr, uid, ids, journal_id=False,
                              group=False, type='out_invoice', context=None):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        if context is None:
            context = {}

        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        partner_obj = self.pool.get('res.partner')
        invoices_group = {}
        res = {}
        inv_type = type
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.invoice_state != '2binvoiced':
                continue
            partner = self._get_partner_to_invoice(cr, uid, picking, context=context)
            if isinstance(partner, int):
                partner = partner_obj.browse(cr, uid, [partner], context=context)[0]
            if not partner:
                raise osv.except_osv(_('Error, no partner!'),
                                     _('Please put a partner on the picking list if you want to generate invoice.'))

            if not inv_type:
                inv_type = self._get_invoice_type(picking)

            if group and partner.id in invoices_group:
                invoice_id = invoices_group[partner.id]
                invoice = invoice_obj.browse(cr, uid, invoice_id)
                invoice_vals_group = self._prepare_invoice_group(cr, uid, picking, partner, invoice, context=context)
                invoice_obj.write(cr, uid, [invoice_id], invoice_vals_group, context=context)
            else:
                invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
                invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                invoices_group[partner.id] = invoice_id
            res[picking.id] = invoice_id
            for move_line in picking.move_lines:
                if move_line.state == 'cancel':
                    continue
                if move_line.scrapped:
                    # do no invoice scrapped products
                    continue
                vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                                                  invoice_id, invoice_vals, context=context)
                if vals:
                    vals['sale_id'] = move_line.sale_line_id.order_id.id
                    vals['wf_create'] = True
                    invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)
                    self._invoice_line_hook(cr, uid, move_line, invoice_line_id)
                    move_line.write({'invoice_line_id': invoice_line_id})

            invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                                       set_total=(inv_type in ('in_invoice', 'in_refund')))
            self.write(cr, uid, [picking.id], {
                'invoice_state': 'invoiced',
            }, context=context)
            self._invoice_hook(cr, uid, picking, invoice_id)
        self.write(cr, uid, res.keys(), {
            'invoice_state': 'invoiced',
        }, context=context)
        return res

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids, context=context):
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            partial_qty_kg, move_product_qty_kg, note, color_id_temp, lot, roll = {}, {}, {}, {}, {}, {}
            qty_kg_real, qty_yrd_real, price_unit, processing_price = {}, {}, {}, {}
            width, weight = {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s' % (move.id), {})
                product_qty = partial_data.get('product_qty', 0.0)
                qty_kg = partial_data.get('qty_kg', 0.0)
                color_id = partial_data.get('color_id', False)
                note_temp = partial_data.get('note') or ''
                lot_temp = partial_data.get('lot') or ''
                roll_temp = partial_data.get('roll') or ''
                width_temp = partial_data.get('width') or ''
                weight_temp = partial_data.get('weight') or ''
                qty_kg_real_temp = partial_data.get('qty_kg_real') or 0
                qty_yrd_real_temp = partial_data.get('qty_yrd_real') or 0
                price_unit_temp = partial_data.get('price_unit') or 0
                processing_price_temp = partial_data.get('processing_price') or 0
                move_product_qty[move.id] = product_qty
                move_product_qty_kg[move.id] = qty_kg
                color_id_temp[move.id] = color_id
                note.update({
                    move.id: note_temp or '',
                })
                lot.update({
                    move.id: lot_temp or '',
                })
                roll.update({
                    move.id: roll_temp or '',
                })
                width.update({
                    move.id: width_temp or '',
                })
                weight.update({
                    move.id: weight_temp or '',
                })
                qty_kg_real.update({
                    move.id: qty_kg_real_temp or 0,
                })
                qty_yrd_real.update({
                    move.id: qty_yrd_real_temp or 0,
                })
                price_unit.update({
                    move.id: price_unit_temp or 0,
                })
                processing_price.update({
                    move.id: processing_price_temp or 0,
                })

                product_uom = partial_data.get('product_uom', False)
                product_price = partial_data.get('product_price', 0.0)
                product_currency = partial_data.get('product_currency', False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty,
                                                            move.product_uom.id)
                partial_qty_kg[move.id] = qty_kg
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)

                # Average price computation
                if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                    product = product_obj.browse(cr, uid, move.product_id.id)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)

                    if product.id not in product_avail:
                        # keep track of stock on hand including processed lines not yet marked as done
                        product_avail[product.id] = product.qty_available

                    if qty > 0:
                        new_price = currency_obj.compute(cr, uid, product_currency,
                                                         move_currency_id, product_price, round=False)
                        new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                                                           product.uom_id.id)
                        if product_avail[product.id] <= 0:
                            product_avail[product.id] = 0
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get('standard_price', context=context)[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id]) \
                                             + (new_price * qty)) / (product_avail[product.id] + qty)
                        # Write the field according to price type field
                        product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation is enabled.
                        move_obj.write(cr, uid, [move.id],
                                       {'price_unit': product_price,
                                        'price_currency_id': product_currency})

                        product_avail[product.id] += qty

            for move in too_few:
                product_qty = move_product_qty[move.id]
                product_qty_kg = move_product_qty_kg[move.id]
                color_id = color_id_temp[move.id]
                note_temp = note[move.id]
                lot_temp = lot[move.id]
                roll_temp = roll[move.id]
                width_temp = width[move.id]
                weight_temp = weight[move.id]

                qty_kg_real_temp = qty_kg_real[move.id]
                qty_yrd_real_temp = qty_yrd_real[move.id]
                price_unit_temp = price_unit[move.id]
                processing_price_temp = processing_price[move.id]

                if not new_picking:
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id],
                               {'name': sequence_obj.get(cr, uid,
                                                         'stock.picking.%s' % (pick.type)),
                               })
                    new_picking = self.copy(cr, uid, pick.id,
                                            {
                                                'name': new_picking_name,
                                                'move_lines': [],
                                                'state': 'draft',
                                            })
                if product_qty != 0:
                    defaults = {
                        'product_qty': product_qty,
                        'qty_kg': product_qty_kg,
                        'note': note_temp,
                        'lot': lot_temp,
                        'roll': roll_temp,
                        'width': width_temp,
                        'weight': weight_temp,

                        'qty_kg_real': qty_kg_real_temp,
                        'qty_yrd_real': qty_yrd_real_temp,
                        'price_unit': price_unit_temp,
                        'processing_price': processing_price_temp,

                        'color_id': color_id,
                        'product_uos_qty': product_qty,
                        'picking_id': new_picking,
                        'state': 'assigned',
                        'move_dest_id': False,
                        'product_uom': product_uoms[move.id]
                    }

                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)

                move_obj.write(cr, uid, [move.id],
                               {
                                   'product_qty': move.product_qty - partial_qty[move.id],
                                   'qty_kg': move.qty_kg - partial_qty_kg[move.id],
                                   'product_uos_qty': move.product_qty - partial_qty[move.id],
                                   # TODO: put correct uos_qty
                                   'prodlot_id': False,
                                   'tracking_id': False,
                               })
            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                note_temp = note[move.id]
                qty_kg_real_temp = qty_kg_real[move.id]
                qty_yrd_real_temp = qty_yrd_real[move.id]
                price_unit_temp = price_unit[move.id]
                processing_price_temp = processing_price[move.id]

                roll_temp = roll[move.id]
                lot_temp = lot[move.id]
                width_temp = width[move.id]
                weight_temp = weight[move.id]
                defaults = {'product_uom': product_uoms[move.id],
                            'qty_kg': move_product_qty_kg[move.id],
                            'note': note_temp or '',
                            'roll': roll_temp or '',
                            'lot': lot_temp or '',
                            'width': width_temp or '',
                            'weight': weight_temp or '',

                            'qty_kg_real': qty_kg_real_temp or '',
                            'qty_yrd_real': qty_yrd_real_temp or '',
                            'price_unit': price_unit_temp or '',
                            'processing_price': processing_price_temp or '',

                            'color_id': color_id_temp[move.id],
                            'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                qty_kg = move_product_qty_kg[move.id]
                note_temp = note[move.id]
                roll_temp = roll[move.id]
                lot_temp = lot[move.id]
                width_temp = width[move.id]
                weight_temp = weight[move.id]
                qty_kg_real_temp = qty_kg_real[move.id]
                qty_yrd_real_temp = qty_yrd_real[move.id]
                price_unit_temp = price_unit[move.id]
                processing_price_temp = processing_price[move.id]
                defaults = {
                    'product_qty': product_qty,
                    'qty_kg': qty_kg,
                    'note': note_temp or '',
                    'roll': roll_temp or '',
                    'lot': lot_temp or '',
                    'width': width_temp or '',
                    'weight': weight_temp or '',
                    'qty_kg_real': qty_kg_real_temp or '',
                    'qty_yrd_real': qty_yrd_real_temp or '',
                    'price_unit': price_unit_temp or '',
                    'processing_price': processing_price_temp or '',

                    'color_id': color_id_temp[move.id],
                    'product_uos_qty': product_qty,  # TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                delivered_pack_id = pick.id
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, new_picking,
                                  body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name),
                                  context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res

    def action_cancel(self, cr, uid, ids, context=None):
        # ### INIT-quan : overwite ham cancel picking
        history_factory_detail_obj = self.pool.get('history.factory.detail')
        for pick in self.browse(cr, uid, ids, context=context):
            ids2 = [move.id for move in pick.move_lines]
            for move_line in pick.move_lines:
                lst_history_detail = history_factory_detail_obj.search(cr, uid, [('move_id', '=', move_line.id)],
                                                                       context=context)
                history_factory_detail_obj.unlink(cr, 1, lst_history_detail, context=context)

            self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
        self.write(cr, uid, ids, {'state': 'cancel', 'invoice_state': 'none'})
        return True


class stock_picking_in(osv.osv):
    _inherit = 'stock.picking.in'
    _columns = {
        'init_warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',
                                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'date_done': fields.datetime('Date of Transfer'),
        'sale_line_id': fields.related('move_lines', 'sale_line_id', type='many2one', relation='sale.order.line',
                                       string='Sale'),
        'section_id': fields.many2one('production.section', 'Section',
                                      states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'user_id': fields.many2one('res.users', 'User'),
    }

    _defaults = {
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):
        return move_line.price_unit

    def set_to_draft_init(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def set_to_done_init(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)


class stock_picking_out(osv.osv):
    _inherit = 'stock.picking.out'
    _columns = {
        'date_done': fields.datetime('Date of Transfer'),
        'sale_line_id': fields.related('move_lines', 'sale_line_id', type='many2one', relation='sale.order.line',
                                       string='Sale'),
        'section_id': fields.many2one('production.section', 'Section',
                                      states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'init_warehouse_id': fields.many2one('stock.warehouse', 'Warehouse',
                                        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'user_id': fields.many2one('res.users', 'User'),
    }

    _defaults = {
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        if not warehouse_id and not ids:
            return {}
        for picking in self.browse(cr, uid, ids):
            warehouse = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
            if picking.move_lines:
                for f in picking.move_lines:
                    self.pool.get('stock.move').write(cr, uid, [f.id], {'location_id': warehouse.lot_stock_id.id})
        return {'value': {}}

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        return super(stock_picking, self).do_partial(cr, uid, ids, partial_datas, context=context)

    def set_to_draft_init(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def set_to_done_init(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)
