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

from dateutil.relativedelta import relativedelta
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.float_utils import float_is_zero
from openerp.tools.translate import _
from openerp import netsvc


class create_in_finished_wizard(osv.osv_memory):
    _name = "create.in.finished.wizard"

    def default_get(self, cr, uid, fields, context):
        if context is None:
            context = {}
        res = super(create_in_finished_wizard, self).default_get(cr, uid, fields, context=context)
        obj_section = self.pool.get('production.section').browse(cr, uid, context['active_ids'])
        obj_material = obj_section and (obj_section[0].finished_ids and obj_section[0].finished_ids or []) or []
        if obj_section[0].plan_id.state != 'confirm':
            raise osv.except_osv(_('Warning'), _('You just only do it when plan is in proccess'))
        # TO DO: select Section have min sequence 
        result = []
        if obj_material:
            for line in obj_material:
                dic = {
                    'product_id': obj_section[0].product_id and obj_section[0].product_id.id or False,
                    'product_uom': obj_section[0].product_id.uom_id and obj_section[0].product_id.uom_id.id or False,
                    'quantity': (line.quantity - (line.qty_out3 or 0)) or 0,
                    'qty_kg': (line.qty_kg - (line.qty_kg_out3 or 0)) or 0,
                    'finished_id': line.id,
                    'price_unit': obj_section[0].price or 0,
                }
                result.append(dic)
            res['finished_ids'] = result
        res['section_id'] = context['active_ids'][0]
        res.update({
            'sale_id': obj_section[0].plan_id.sale_line_id.order_id.id,
            'partner_id': obj_section[0].plan_id.sale_line_id.order_id.partner_id.id,
            'lc': obj_section[0].plan_id.sale_line_id.order_id.lc or '', })
        return res

    def default_date(self, cr, uid, context):
        cr.execute("""SELECT MIN(p_f.date_out) AS min_date
                FROM production_finished p_f
                LEFT JOIN  production_section p_s ON (p_s.id = p_f.section_finished_id)
                    WHERE p_s.id = '%s' """ % (context['active_ids'][0]))
        return cr.fetchone()[0]

    def default_stock_id(self, cr, uid, context):
        if not context: context = {}
        obj_section = self.pool.get('production.section').browse(cr, uid, context['active_ids'])[0]
        condition = []
        for obj in obj_section.history_fact_ids:
            if obj.out_material_ids and obj.stock_id:
                condition.append(obj.stock_id.id)
        if condition:
            return condition[0]
        return

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        """
            Add domain 'allow_check_writing = True' on journal_id field and remove 'widget = selection' on the same
            field because the dynamic domain is not allowed on such widget
        """
        if not context: context = {}
        res = super(create_in_finished_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                                     context=context, toolbar=toolbar, submenu=submenu)
        fields = res.get('fields', {})
        if fields:
            if fields.get('stock_id') and context.get('active_ids', False):
                obj_section = self.pool.get('production.section').browse(cr, uid, context['active_ids'])[0]
                condition = []
                for obj in obj_section.history_fact_ids:
                    if obj.out_material_ids and obj.stock_id:
                        condition.append(obj.stock_id.id)
                res['fields']['stock_id']['domain'] = [('id', 'in', condition)]
        return res


    _columns = {
        'partner_id': fields.many2one('res.partner', 'Supplier', required=True),
        'section_id': fields.many2one('production.section', 'Section', required=True),
        'date_order': fields.date('Date', required=True),
        'stock_id': fields.many2one('stock.warehouse', 'Factory ', required=True),
        'note': fields.text('Notes'),
        'finished_ids': fields.one2many('production.finished.wizard', 'finished_id_wizard', 'Finished'),
        'sale_id': fields.many2one('sale.order', 'Sale Order', readonly=True),
        'lc': fields.char('L/C', size=256, readonly=True),
        'material_ids': fields.one2many('production.material.pre.wizard', 'material_id_wizard', 'Material'),
    }

    _defaults = {
        'date_order': default_date,
        'stock_id': default_stock_id,
    }

    def onchange_stock_id(self, cr, uid, ids, stock_id, context={}):
        if not stock_id:
            return {'value': {}}
        partner_obj = self.pool.get('stock.warehouse').browse(cr, uid, stock_id).partner_id
        return {'value': {'partner_id': partner_obj and partner_obj.id or False}}

    def button_validate(self, cr, uid, ids, context={}):
        # TO DO: check stock have product or have not product
        #Incoming shipment product finished from manufacturing's location to Factory's location
        obj_finished = self.browse(cr, uid, ids)[0]
        obj_line = self.browse(cr, uid, ids)[0].finished_ids
        obj_section = self.pool.get('production.section').browse(cr, uid, context['active_ids'])
        wf_service = netsvc.LocalService("workflow")
        p_in_id = self.pool.get('stock.picking').create(cr, uid, {
            'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in'),
            'type': 'in',
            'partner_id': obj_finished.partner_id.id,
            'date': obj_finished.date_order,
            'invoice_state': '2binvoiced',
        })
        fact_ids = self.pool.get('history.factory').search(cr, uid, [('stock_id', '=', int(obj_finished.stock_id.id)),
                                                                     (
                                                                         'section_fact_id', '=',
                                                                         context['active_ids'][0])])
        fact_id = fact_ids and fact_ids[0] or False
        if not fact_id:
            fact_id = self.pool.get('history.factory').create(cr, uid, {'stock_id': obj_finished.stock_id.id or False,
                                                                        'section_fact_id': context['active_ids'][0], })
        for line in obj_line:
            line.finished_id.write({'qty_out3': line.finished_id.qty_out3 + line.quantity})
            line.finished_id.write({'qty_kg_out3': line.finished_id.qty_kg_out3 + line.qty_kg})
            if line.quantity > 0:
                color_id = False
                if obj_section[0].plan_id and obj_section[0].plan_id.sale_line_id.product_id == obj_section[
                    0].product_id:
                    if obj_section[0].plan_id.sale_line_id.color_id:
                        color_id = obj_section[0].plan_id.sale_line_id.color_id.id

                new_move_id = self.pool.get('stock.move').create(cr, uid, {
                    'name': obj_finished.note or '/',
                    'product_id': obj_section[0].product_id and obj_section[0].product_id.id or False,
                    'product_qty': line.quantity or 0,
                    'qty_kg': line.qty_kg or 0,
                    'weight': line.weight_prod or 0,
                    'width': line.width or 0,
                    'product_uom': line.product_uom.id or False,
                    'price_unit': line.price_unit or 0,
                    'location_id': obj_section[0].product_id and (obj_section[0].product_id.property_stock_production \
                                                                  and obj_section[
                        0].product_id.property_stock_production.id \
                                                                  or False) or False,
                    'location_dest_id': obj_finished.stock_id and obj_finished.stock_id.lot_stock_id.id or False,
                    'sale_line_id': obj_section[0].plan_id and obj_section[0].plan_id.sale_line_id.id or False,
                    'color_id': color_id,
                    'lot': line.lot or '',
                    'roll': line.roll or '',
                    'section_id': context['active_ids'][0],
                    'picking_id': p_in_id,
                    'state': 'done'
                })
                self.pool.get('history.section').create(cr, uid, {
                    'product_id': obj_section[0].product_id and obj_section[0].product_id.id or False,
                    'quantity': line.quantity or 0,
                    'user_id': obj_section[0].user_id and obj_section[0].user_id.id or False,
                    'location_id': obj_section[0].product_id and (obj_section[0].product_id.property_stock_production \
                                                                  and obj_section[
                        0].product_id.property_stock_production.id \
                                                                  or False) or False,
                    'location_dest_id': obj_finished.stock_id and obj_finished.stock_id.lot_stock_id.id or False,
                    'des': 'infactory',
                })
                self.pool.get('history.factory.detail').create(cr, uid, {
                    'product_id': line.product_id and line.product_id.id or False,
                    'quantity': line.quantity or 0,
                    'qty_kg': line.qty_kg or 0,
                    'roll': line.roll or '',
                    'user_id': obj_section[0].user_id and obj_section[0].user_id.id or False,
                    'date': obj_finished.date_order or False,
                    'type': 'in_finished',
                    'factory_id': fact_id,
                    'move_id': new_move_id,
                    'price_unit': line.price_unit or 0,
                    'warehouse_id': obj_finished.stock_id.id,
                })
        wf_service.trg_validate(uid, 'stock.picking', p_in_id, 'button_confirm', cr)
        wf_service.trg_validate(uid, 'stock.picking', p_in_id, 'button_done', cr)
        return {}


create_in_finished_wizard()


class production_finished_wizard(osv.osv_memory):
    _name = "production.finished.wizard"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'finished_id': fields.many2one('production.finished', 'Finished', required=True),
        'quantity': fields.float('Qty(Kg)'),
        'qty_kg': fields.float('Qty(Yard)'),
        'price_unit': fields.float('Price Unit'),
        'product_uom': fields.many2one('product.uom', 'UoM', required=True),
        'finished_id_wizard': fields.many2one('create.in.finished.wizard', 'Finished'),
        'lot': fields.char('Lot', size=256),
        'roll': fields.char('Roll', size=256),
        'weight_prod': fields.float('Weight'),
        'width': fields.float('Width'),
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


production_finished_wizard()


