# -*- coding: utf-8 -*-
# #############################################################################
#
# OpenERP, Open Source Management Solution
# Copyright (C) 2013 INIT TECH (<http://init.vn>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
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

from operator import itemgetter

from openerp.osv import fields, osv
from openerp import netsvc
from openerp.tools.translate import _


class internal_order(osv.osv):
    _name = 'internal.order'
    _description = 'Internal Order'

    _columns = {
        'name': fields.char('Number', size=64, required=True),
        'date_order': fields.date('Date', required=True),
        'date_confirm': fields.date('Confirmation Date'),
        'user_id': fields.many2one('res.users', 'User'),

        'sol_to_id': fields.many2one('sale.order.line', 'Sale Order Line To', required=True),
        'sol_from_id': fields.many2one('sale.order.line', 'Sale Order Line From', required=True),
        'section_to_id': fields.many2one('production.section', 'Section To', required=True),
        'section_from_id': fields.many2one('production.section', 'Section From', required=True),
        'warehouse_to_id': fields.many2one('stock.warehouse', 'Warehouse To', required=True),
        'warehouse_from_id': fields.many2one('stock.warehouse', 'Warehouse From', required=True),
        'state': fields.selection([
                                      ('draft', 'Draft'),
                                      ('done', 'Done'),
                                      ('cancel', 'Cancel'),
                                  ], 'Status'),


        'order_line': fields.one2many('internal.order.line', 'order_id', 'Lines'),
    }

    _defaults = {
        'date_order': fields.date.context_today,
        'state': 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def onchange_sol_id(self, cr, uid, ids, sol_from_id, sol_to_id, context=None):
        if context is None:
            context = {}
        list_section_from = []
        list_warehouse_from = []
        list_section_to = []
        list_warehouse_to = []
        list_move = []
        ###### domain for from
        if sol_from_id:
            cr.execute("""SELECT ps.id
                            FROM production_section ps
                                INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                                INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id)         
                            WHERE 
                                sol.id = %s
                                """ % (sol_from_id))
            seq = map(itemgetter(0), cr.fetchall())
            list_section_from = list(set(seq))

            cr.execute("""SELECT sw.id
                            FROM stock_move sm
                                INNER JOIN stock_warehouse sw on (sm.location_dest_id = sw.lot_stock_id) 
                            WHERE 
                                sm.sale_line_id = %s
                                """ % (sol_from_id))
            seq1 = map(itemgetter(0), cr.fetchall())
            list_warehouse_from = list(set(seq1))

            ###### domain for to
        if sol_to_id:
            cr.execute("""SELECT ps.id
                            FROM production_section ps
                                INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                                INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id)         
                            WHERE 
                                sol.id = %s
                                """ % (sol_to_id))
            seq = map(itemgetter(0), cr.fetchall())
            list_section_to = list(set(seq))
            cr.execute("""SELECT sw.id
                            FROM stock_move sm
                                INNER JOIN stock_warehouse sw on (sm.location_dest_id = sw.lot_stock_id) 
                            WHERE 
                                sm.sale_line_id = %s
                                """ % (sol_to_id))
            seq1 = map(itemgetter(0), cr.fetchall())
            list_warehouse_to = list(set(seq1))

        return {'domain': {
            'section_from_id': [('id', 'in', list_section_from)],
            'section_to_id': [('id', 'in', list_section_to)],

            'warehouse_from_id': [('id', 'in', list_warehouse_from)],
            'warehouse_to_id': [('id', 'in', list_warehouse_to)],
        }
        }


    def action_transfer(self, cr, uid, ids, context=None):
        # TO DO: check stock have product or have not product
        # Create DO and IO 
        wf_service = netsvc.LocalService("workflow")
        move_obj = self.pool.get('stock.move')
        history_factory_obj = self.pool.get('history.factory')
        history_factory_detail_obj = self.pool.get('history.factory.detail')
        picking_obj = self.pool.get('stock.picking')

        location_customer_id = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'customer')])[0]
        location_supplier_id = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'supplier')])[0]

        for obj in self.browse(cr, uid, ids, context):
            section_from = obj.section_from_id
            section_to = obj.section_to_id
            warehouse_from = obj.warehouse_from_id
            warehouse_to = obj.warehouse_to_id
            date_order = obj.date_order
            location_id = warehouse_from.lot_stock_id.id or False
            location_dest_id = warehouse_to.lot_stock_id.id or False
            section_from = obj.section_from_id
            section_to = obj.section_to_id
            warehouse_from = obj.warehouse_from_id
            warehouse_to = obj.warehouse_to_id
            date_order = obj.date_order

            picking_out_id = picking_obj.create(cr, uid, {
                'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out'),
                'date': date_order,
                'type': 'out',
                'internal_id': obj.id,
            })
            picking_in_id = self.pool.get('stock.picking').create(cr, uid, {
                'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in'),
                'date': date_order,
                'type': 'in',
                'internal_id': obj.id,
            })
            for line in obj.order_line:
                new_ctx = {'uom': line.product_uom.id}
                check = self.pool.get('stock.location')._product_reserve(cr, uid, [location_id], line.product_id.id,
                                                                         line.qty, new_ctx, lock=True)
                if not check:
                    raise osv.except_osv(_('Error!'), _("Not enough quantity."))
                if line.qty > 0:
                    #### Write in history
                    product_id = line.product_id and line.product_id.id or False
                    #### DO
                    move_id_out = self.pool.get('stock.move').create(cr, uid, {
                        'name': '/',
                        'product_id': product_id,
                        'product_qty': line.qty or 0.0,
                        'qty_kg': line.qty_kg or 0.0,
                        'product_uom': line.product_uom and line.product_uom.id or False,
                        'location_id': location_id,
                        'location_dest_id': location_customer_id,
                        'picking_id': picking_out_id,
                        'lot': line.lot or '',
                        'roll': line.roll or '',
                        'width': line.width or '',
                        'weight': line.weight or '',
                        'note': line.note or '',
                        'sale_line_id': line.order_id.sol_from_id.id or False,
                        'section_id': line.order_id.section_from_id.id or False,
                        'note': obj.name or '',
                    })
                    #### history DO
                    fact_from_id = history_factory_obj.search(cr, uid, [('stock_id', '=', warehouse_from.id),
                                                                        ('section_fact_id', '=', section_from.id)])[0]
                    if product_id == section_from.product_id.id:
                        product_out_id = history_factory_detail_obj.create(cr, uid, {
                            'product_id': product_id,
                            'quantity': -line.qty or 0.0,
                            'date': date_order,
                            'user_id': uid,
                            'type': 'in_finished',
                            'factory_id' : fact_from_id,
                            'warehouse_id': warehouse_from.id,
                            'move_id': move_id_out,
                        })
                    else:
                        if product_id in [line.product_id.id for line in section_from.material_ids]:
                            product_out_id = history_factory_detail_obj.create(cr, uid, {
                                'product_id': product_id,
                                'quantity': line.qty or 0.0,
                                'date': date_order,
                                'user_id': uid,
                                'type': 'out_material',
                                'factory_id' : fact_from_id,
                                'warehouse_id': warehouse_from.id,
                                'move_id': move_id_out,
                            })
                    #### IN
                    move_id_in = self.pool.get('stock.move').create(cr, uid, {
                        'name': '/',
                        'product_id': product_id,
                        'product_qty': line.qty or 0.0,
                        'qty_kg': line.qty_kg or 0.0,
                        'product_uom': line.product_uom and line.product_uom.id or False,

                        'location_id': location_supplier_id,
                        'location_dest_id': location_dest_id,
                        'picking_id': picking_in_id,
                        'lot': line.lot or '',
                        'roll': line.roll or '',
                        'width': line.width or '',
                        'weight': line.weight or '',
                        'note': line.note or '',
                        'sale_line_id': line.order_id.sol_to_id.id or False,
                        'section_id': line.order_id.section_to_id.id or False,
                        'note': obj.name or '',
                    })
                    #### history IN
                    fact_to_id = history_factory_obj.search(cr, uid, [('stock_id', '=', warehouse_to.id),
                                                                        ('section_fact_id', '=', section_to.id)])[0]
                    if product_id == section_to.product_id.id:
                        product_out_id = history_factory_detail_obj.create(cr, uid, {
                            'product_id': product_id,
                            'quantity': -(line.qty) or 0.0,
                            'date': date_order,
                            'user_id': uid,
                            'type': 'in_finished',
                            'factory_id' : fact_to_id,
                            'warehouse_id': warehouse_to.id,
                            'move_id': move_id_out,
                        })
                    else:
                        product_out_id = history_factory_detail_obj.create(cr, uid, {
                            'product_id': product_id,
                            'quantity': (line.qty) or 0.0,
                            'date': date_order,
                            'user_id': uid,
                            'type': 'in_material',
                            'factory_id' : fact_to_id,
                            'warehouse_id': warehouse_to.id,
                            'move_id': move_id_in,
                        })

            wf_service.trg_validate(uid, 'stock.picking', picking_out_id, 'button_confirm', cr)
            self.pool.get('stock.picking').action_move(cr, uid, [picking_out_id], context=context)
            wf_service.trg_validate(uid, 'stock.picking', picking_out_id, 'button_done', cr)

            wf_service.trg_validate(uid, 'stock.picking', picking_in_id, 'button_confirm', cr)
            self.pool.get('stock.picking').action_move(cr, uid, [picking_in_id], context=context)
            wf_service.trg_validate(uid, 'stock.picking', picking_in_id, 'button_done', cr)

        self.write(cr, uid, ids, {'state': 'done'})
        return {}

    def action_cancel(self, cr, uid, ids, context=None):
        picking_obj = self.pool.get('stock.picking')
        for obj in self.browse(cr, uid, ids, context):
            lst_picking = picking_obj.search(cr, uid, [('internal_id', '=', obj.id)])
            picking_obj.action_revert_done(cr, uid, lst_picking, context=context)
            picking_obj.unlink(cr, uid, lst_picking, context=context)
        self.write(cr, uid, ids, {'state': 'cancel'})
        return {}


class internal_order_line(osv.osv):
    _name = 'internal.order.line'
    _description = 'Internal Order Line'

    _columns = {
        'order_id': fields.many2one('internal.order', 'Internal Order'),

        'product_id': fields.many2one('product.product', 'Product', required=True),
        'color_id': fields.many2one('product.color', 'Color'),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True),

        'lot': fields.char('Lot', size=256),
        'roll': fields.char('Roll', size=256),
        'note': fields.text('Note', size=256),
        'width': fields.char('Width', size=256),
        'weight': fields.char('Weight', size=256),

        'qty': fields.float('Qty(Kg)', required=True),
        'qty_kg': fields.float('Qty(Yard)'),

    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
