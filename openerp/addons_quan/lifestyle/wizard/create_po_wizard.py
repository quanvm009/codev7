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
from datetime import datetime

import openerp.addons.decimal_precision as dp
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
from openerp import netsvc


class create_po_wizard(osv.osv_memory):
    _name = "create.po.wizard"

    def default_get(self, cr, uid, fields, context):
        if context is None:
            context = {}
        section_obj = self.pool.get('production.section')
        res = super(create_po_wizard, self).default_get(cr, uid, fields, context=context)
        obj_plan = self.pool.get('production.plan').browse(cr, uid, context['active_ids'])
        lst_section = section_obj.search(cr, uid, [('plan_id', '=', context['active_ids'][0])], context=context)
        lst_material_id = []
        lst_finished_id = []
        for section in section_obj.browse(cr, uid, lst_section, context=context):
            lst_material_id += [line.product_id.id for line in
                                section_obj.browse(cr, uid, section.id, context=context).material_ids]

            lst_finished_id.append(section.product_id.id)
        lst_material_id = list(set(lst_material_id))
        lst_finished_id = list(set(lst_finished_id))
        lst_material_id = [n for n in lst_material_id if n not in lst_finished_id]

        list_obj_section = self.pool.get('production.section').browse(cr, uid, lst_section)
        result = []
        for obj_section in list_obj_section:
            for line in obj_section.material_ids:
                if line.product_id.id in lst_material_id:
                    dic = {
                        'product_id': line.product_id and line.product_id.id or False,
                        'product_uom': line.product_uom and line.product_uom.id or False,
                        'qty_kg': line.qty_kg or 0.0,
                        'quantity': line.quantity or 0,
                        'sale_line_id': obj_plan[0].sale_line_id.id or False,
                    }
                    result.append(dic)
        res['material_ids'] = result
        return res

    def _get_default_warehouse(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [('company_id', '=', company_id)],
                                                                context=context)
        if not warehouse_ids:
            raise osv.except_osv(_('Error!'), _('There is no default warehouse for the current user\'s company!'))
        return warehouse_ids[0]

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Supplier', required=True),
        'stock_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'date_order': fields.date('Date Order', required=True),
        'material_ids': fields.one2many('production.material.wizard', 'material_id_wizard', 'Materials'),
    }
    _defaults = {
        'date_order': lambda *a: datetime.now().strftime('%Y-%m-%d'),
        'stock_id': _get_default_warehouse,
    }

    def button_validate(self, cr, uid, ids, context={}):
        obj_material = self.browse(cr, uid, ids)[0]
        obj_plan = self.pool.get('production.plan').browse(cr, uid, context['active_ids'])
        p_id = self.pool.get('purchase.order').create(cr, uid, {'partner_id': obj_material.partner_id.id,
                                                                'date_order': obj_material.date_order,
                                                                'location_id': obj_material.stock_id and obj_material.stock_id.lot_stock_id.id or False,
                                                                'warehouse_id': obj_material.stock_id.id,
                                                                'pricelist_id': 1,
        })
        obj_line = self.browse(cr, uid, ids)[0].material_ids
        wf_service = netsvc.LocalService("workflow")
        for line in obj_line:
            self.pool.get('purchase.order.line').create(cr, uid, {
                'product_id': line.product_id and line.product_id.id or False,
                'name': line.product_id and line.product_id.name or '',
                'product_qty': line.quantity or 0,
                'qty_kg': line.qty_kg or 0.0,
                'product_uom': line.product_uom and line.product_uom.id or False,
                # 'price_unit': line.product_id and line.product_id.list_price or 0,
                'order_id': p_id,
                'date_planned': time.strftime('%Y-%m-%d'),
                'sale_line_id': line.sale_line_id.id or False,
                'price_unit': line.price_unit,
            })
            self.pool.get('history.plan').create(cr, uid, {
                'product_id': line.product_id and line.product_id.id or False,
                'quantity': line.quantity or 0,
                'user_id': obj_plan[0].user_id and obj_plan[0].user_id.id or False,
                'date_create': obj_plan[0].date_create or False,
                'plan_id': context['active_ids'][0],
                'stock_id': obj_material.stock_id.id,
            })

        wf_service.trg_validate(uid, 'purchase.order', p_id, 'purchase_confirm', cr)

        return {
            'name': _('Incoming Shipment'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'stock.picking.in',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'domain': "[('purchase_id','=',%d)]" % (p_id)
        }

        def button_cancel(self, cr, uid, ids, context=None):
            return


create_po_wizard()


class production_material_wizard(osv.osv_memory):
    _name = "production.material.wizard"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'quantity': fields.float('Qty(Kg)'),
        'qty_kg': fields.float('Qty(Yard)'),
        'product_uom': fields.many2one('product.uom', 'UoM'),
        'sale_line_id': fields.many2one('sale.order.line', 'Sale Order Line'),
        'material_id_wizard': fields.many2one('create.po.wizard', 'Material'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price')),
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


production_material_wizard()




