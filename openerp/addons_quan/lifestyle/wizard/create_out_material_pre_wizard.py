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

import time
from openerp.addons.lifestyle.model.datetime_utils import *

from dateutil.relativedelta import relativedelta
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.float_utils import float_is_zero
from openerp.tools.translate import _
from openerp import netsvc


class create_out_material_pre_wizard(osv.osv_memory):
    _name = "create.out.material.pre.wizard"

    def default_get(self, cr, uid, fields, context):
        if context is None:
            context = {}
        res = super(create_out_material_pre_wizard, self).default_get(cr, uid, fields, context=context)
        obj_section = self.pool.get('production.section').browse(cr, uid, context['active_ids'])
        obj_material = obj_section and (obj_section[0].material_ids and obj_section[0].material_ids or []) or []
        if obj_section[0].plan_id.state != 'confirm':
            raise osv.except_osv(_('Warning'), _('You just only do it when plan is in proccess'))
        # TO DO: select Section have min sequence 
        result = []
        if obj_material:
            for line in obj_material:
                dic = {
                    'product_id': line.product_id and line.product_id.id or False,
                    'product_uom': line.product_uom and line.product_uom.id or False,
                    'quantity': (line.quantity - (line.qty_out or 0)) or 0,
                    'qty_kg': (line.qty_kg - (line.qty_kg_out or 0)) or 0,
                    'section_id': line.section_id and line.section_id.id or False,
                    'material_id': line.id,

                }
                if line.quantity - line.qty_out > 0:
                    result.append(dic)
            res['material_ids'] = result

        res.update({
            'sale_id': obj_section[0].plan_id.sale_line_id.order_id.id,
            'partner_id': obj_section[0].plan_id.sale_line_id.order_id.partner_id.id,
            'lc': obj_section[0].plan_id.sale_line_id.order_id.lc or '',
            'stock_id': obj_section[0].stock_plan_id.id,
        })
        return res

    def onchange_stock_id(self, cr, uid, ids, stock_id, context=None):
        if not stock_id:
            return {'value': {}}
        res = {}
        res['material_ids'] = []
        obj_section = self.pool.get('production.section').browse(cr, uid, context['active_ids'])[0]
        obj_material = obj_section and (obj_section.material_ids and obj_section.material_ids or []) or []

        product_ids = []

        for line in obj_material:

            if line.product_id in product_ids:
                continue

            product_ids.append(line.product_id)
            new_ctx = {'uom': line.product_uom.id}

            if obj_section.plan_id:
                new_ctx.update(
                    {'sale_line_id': obj_section.plan_id.sale_line_id and obj_section.plan_id.sale_line_id.id or False})

            quantity = self.pool.get('stock.location')._init_get_product_reserve(cr, uid, [
                self.pool.get('stock.warehouse').browse(cr, uid, stock_id).lot_stock_id.id], line.product_id.id,
                                                                                 new_ctx)
            dic = {
                'product_id': line.product_id and line.product_id.id or False,
                'product_uom': line.product_uom and line.product_uom.id or False,
                'quantity': quantity,
                'section_id': context['active_ids'][0],
                'material_id': line.id,
            }
            res['material_ids'].append(dic)
        return {'value': res}

    def default_date(self, cr, uid, context):
        cr.execute("""SELECT MIN(p_m.date_in) AS min_date
                FROM production_material p_m
                LEFT JOIN  production_section p_s ON (p_s.id = p_m.section_material_id)
                    WHERE p_s.id = '%s' """ % (context['active_ids'][0]))
        return cr.fetchone()[0]


    _columns = {
        'partner_id': fields.many2one('res.partner', 'Customer', readonly=True),
        'date_order': fields.date('Date', required=True),
        'note': fields.text('Notes'),
        'stock_id': fields.many2one('stock.warehouse', 'From ', required=True),
        'stock_to_id': fields.many2one('stock.warehouse', 'To Factory', required=True),
        'sale_id': fields.many2one('sale.order', 'Sale Order', readonly=True),
        'lc': fields.char('L/C', size=256, readonly=True),
        'material_ids': fields.one2many('production.material.pre.wizard', 'material_id_wizard', 'Material'),
    }

    _defaults = {
        'date_order': default_date,
    }

    def check_quantity(self, cr, uid, ids, product_ids, context=None):
        obj_product = self.pool.get('product.product')
        for line in product_ids:
            product = obj_product.browse(cr, uid, line.product_id.id)
            if line.quantity > product.qty_available:
                raise osv.except_osv(_('Warning'), _('Product is not enough in inventory '))
        return True

    def button_validate(self, cr, uid, ids, context={}):
        # TO DO: check stock have product or have not product
        # Create Delivery Order from Lifestyle's location to Customer's location
        obj_material = self.browse(cr, uid, ids)[0]
        obj_section = self.pool.get('production.section').browse(cr, uid, context['active_ids'])
        obj_line = obj_material.material_ids

        p_out_id = self.pool.get('stock.picking').create(cr, uid, {
            'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out'),
            'partner_id': obj_material.partner_id.id,
            'date': obj_material.date_order,
            'type': 'out',
        })
        location_id_out = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'customer')])[0]
        self.pool.get('production.section').write(cr, uid, context['active_ids'], {
            'stock_id': obj_material.stock_to_id and obj_material.stock_to_id.id or False})
        fact_ids_to = self.pool.get('history.factory').search(cr, uid,
                                                              [('stock_id', '=', int(obj_material.stock_to_id.id)),
                                                               ('section_fact_id', '=', context['active_ids'][0])])
        fact_ids_from = self.pool.get('history.factory').search(cr, uid,
                                                                [('stock_id', '=', int(obj_material.stock_id.id)),
                                                                 ('section_fact_id', '=', context['active_ids'][0])])
        fact_id_to = fact_ids_to and fact_ids_to[0] or False
        if not fact_id_to:
            fact_id_to = self.pool.get('history.factory').create(cr, uid,
                                                                 {'stock_id': obj_material.stock_to_id.id or False,
                                                                  'section_fact_id': context['active_ids'][0], })
        # fact_id_from = fact_ids_from and fact_ids_from[0] or False
        #        if not fact_id_from:
        #            fact_id_from = self.pool.get('history.factory').create(cr,uid,{ 'stock_id': obj_material.stock_id.id or False,
        #                                                                    'section_fact_id': context['active_ids'][0],})
        wf_service = netsvc.LocalService("workflow")
        for line in obj_line:
            if line.material_id:
                line.material_id.write({'qty_out': line.material_id.qty_out + line.quantity})
                line.material_id.write({'qty_kg_out': line.material_id.qty_kg_out + line.qty_kg})
            if line.quantity > 0:
                new_move_id = self.pool.get('stock.move').create(cr, uid, {'name': obj_material.note or '/',
                                                                           'product_id': line.product_id and line.product_id.id or False,
                                                                           'product_qty': line.quantity or 0,
                                                                           'qty_kg': line.qty_kg or 0,
                                                                           'product_uom': line.product_uom and line.product_uom.id or False,
                                                                           'price_unit': line.product_id and line.product_id.list_price or 0,
                                                                           'location_id': obj_material.stock_id and obj_material.stock_id.lot_stock_id.id or False,
                                                                           'location_dest_id': location_id_out or False,
                                                                           'picking_id': p_out_id,
                                                                           'sale_line_id': obj_section[0].plan_id and
                                                                                           obj_section[
                                                                                               0].plan_id.sale_line_id.id or False,
                                                                           # 'color_id': obj_section[0].plan_id and (
                                                                           # obj_section[0].plan_id.sale_line_id.color_id \
                                                                           # and obj_section[0].plan_id.sale_line_id.color_id.id or False)or False,
                                                                           'lot': line.lot or '',
                                                                           'roll': line.roll or '',
                                                                           'section_id': context['active_ids'][0],
                })
                self.pool.get('history.section').create(cr, uid,
                                                        {'product_id': line.product_id and line.product_id.id or False,
                                                         'quantity': line.quantity or 0,
                                                         'user_id': obj_section[0].user_id and obj_section[
                                                             0].user_id.id or False,
                                                         # 'date_out': line.date_out or False,
                                                         'location_id': obj_material.stock_id and obj_material.stock_id.lot_stock_id.id or False,
                                                         'location_dest_id': obj_material.stock_to_id and obj_material.stock_to_id.lot_stock_id.id or False,
                                                         'section_id': context['active_ids'][0],
                                                         'des': 'lifestyle',
                                                        })

        wf_service.trg_validate(uid, 'stock.picking', p_out_id, 'button_confirm', cr)
        self.pool.get('stock.picking').action_move(cr, uid, [p_out_id], context=context)
        wf_service.trg_validate(uid, 'stock.picking', p_out_id, 'button_done', cr)

        ################################
        # Create Incoming Shipment from Supplier's location to Factroy's location
        ################################
        p_in_id = self.pool.get('stock.picking').create(cr, uid, {
            'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in'),
            'date': obj_material.date_order,
            'type': 'in',
        })

        sale_line_id = obj_section[0].plan_id and (
            obj_section[0].plan_id.sale_line_id and obj_section[0].plan_id.sale_line_id.id or False) or False
        order_line = sale_line_id and self.pool.get('sale.order.line').browse(cr, uid, sale_line_id) or False
        shop_id = order_line and self.pool.get('sale.order').browse(cr, uid, order_line.order_id.id).shop_id.id or False
        location_id_in = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'supplier')])[0]
        for line in obj_line:
            if line.quantity > 0:
                move_id_from = self.pool.get('stock.move').create(cr, uid, {'name': obj_material.note or '/',
                                                                            'product_id': line.product_id and line.product_id.id or False,
                                                                            'product_qty': line.quantity or 0.0,
                                                                            'qty_kg': line.qty_kg or 0.0,
                                                                            'product_uom': line.product_uom and line.product_uom.id or False,
                                                                            'price_unit': line.product_id and line.product_id.list_price or 0,
                                                                            'location_id': location_id_in,
                                                                            'location_dest_id': obj_material.stock_to_id and obj_material.stock_to_id.lot_stock_id.id or False,
                                                                            'picking_id': p_in_id,
                                                                            'sale_line_id': obj_section[0].plan_id and
                                                                                            obj_section[
                                                                                                0].plan_id.sale_line_id.id or False,
                                                                            #                                                                    'color_id': obj_section[0].plan_id and (obj_section[0].plan_id.sale_line_id.color_id \
                                                                            #                                                                                                            and obj_section[0].plan_id.sale_line_id.color_id.id or False)or False,
                                                                            'lot': line.lot or '',
                                                                            'roll': line.roll or '',
                                                                            'section_id': context['active_ids'][
                                                                                              0] or False,
                })
                self.pool.get('history.section').create(cr, uid,
                                                        {'product_id': line.product_id and line.product_id.id or False,
                                                         'quantity': line.quantity or 0,
                                                         'user_id': obj_section[0].user_id and obj_section[
                                                             0].user_id.id or False,
                                                         #                                                        'date_out': line.date_out or False,
                                                         'location_id': location_id_in,
                                                         'location_dest_id': obj_material.stock_to_id and obj_material.stock_to_id.lot_stock_id.id or False,
                                                         'section_id': context['active_ids'][0],
                                                         'des': 'lifestyle',
                                                        })
                self.pool.get('history.factory.detail').create(cr, uid, {
                    'product_id': line.product_id and line.product_id.id or False,
                    'quantity': line.quantity or 0,
                    'qty_kg': line.qty_kg or 0,
                    'roll': line.roll or '',
                    'user_id': obj_section[0].user_id and obj_section[0].user_id.id or False,
                    'date': obj_material.date_order or False,
                    'type': 'in_material',
                    'factory_id': fact_id_to,
                    'warehouse_id': obj_material.stock_id.id,
                    'move_id': new_move_id
                })
        wf_service.trg_validate(uid, 'stock.picking', p_in_id, 'button_confirm', cr)
        wf_service.trg_validate(uid, 'stock.picking', p_in_id, 'button_done', cr)
        return {}


create_out_material_pre_wizard()


class production_material_pre_wizard(osv.osv_memory):
    _name = "production.material.pre.wizard"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'quantity': fields.float('Qty(Kg)'),
        'qty_kg': fields.float('Qty(Yard)'),
        'material_id': fields.many2one('production.material', 'Material'),
        'product_uom': fields.many2one('product.uom', 'UoM'),
        'material_id_wizard': fields.many2one('create.out.material.pre.wizard', 'Material'),
        'section_id': fields.many2one('production.section', 'Section'),
        'lot': fields.char('Lot', size=256),
        'roll': fields.char('Roll', size=256)
    }

    _defaults = {
        'quantity': 0,
        'qty_kg': 0,
    }

    def onchange_product_id(self, cr, uid, ids, prod_id=False, context=None):
        """ On change of product id, .
        @return: Dictionary of values
        """
        if not prod_id:
            return {}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=context)[0]
        result = {
            'product_uom': product.uom_id.id,
        }
        return {'value': result}


production_material_pre_wizard()


