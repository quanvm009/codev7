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
from openerp.osv import osv
from openerp.osv import fields
import openerp.addons.decimal_precision as dp
from operator import itemgetter


class init_section(osv.osv):
    _name = "init.section"
    _columns = {
        'name': fields.char('Name', size=256, required=True),
    }
    _defaults = {
    }


class production_section(osv.osv):
    _name = 'production.section'
    _inherit = ['mail.thread']

    def _get_total_quantity(self, cr, uid, ids, field_names, arg, context=None):
        res = {}

        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.finished_ids:
                for line in obj.finished_ids:
                    total += line.quantity
            res[obj.id] = total
        return res

    def _get_total_qty_kg(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.finished_ids:
                for line in obj.finished_ids:
                    total += line.qty_kg
            res[obj.id] = total
        return res

    def _get_total_quantity_material(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids):
            total = 0
            if obj.material_ids:
                for line in obj.material_ids:
                    total += line.quantity
            res[obj.id] = total
        return res

    def _get_order_finished(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('production.finished').browse(cr, uid, ids, context=context):
            result[line.section_finished_id.id] = True
        return result.keys()

    def _get_order_material(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('production.material').browse(cr, uid, ids, context=context):
            result[line.section_material_id.id] = True
        return result.keys()

    def _get_stock(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids):
            name = ''
            for move in obj.history_fact_ids:
                if move.stock_id:
                    if not name:
                        name += move.stock_id.name or ''
                    else:
                        name += ', %s' % move.stock_id.name
            res[obj.id] = name
        return res

    def _get_sale_id(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[
                order.id] = order and order.plan_id and order.plan_id.sale_line_id and order.plan_id.sale_line_id.order_id.id or False
        return res

    def _sale_search(self, cr, uid, obj, name, args, domain=None, context=None):
        having_values = map(itemgetter(2), args)
        cr.execute("""SELECT ps.id
                        FROM production_section ps
                            INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                            INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id) 
                            INNER JOIN sale_order so on (sol.order_id = so.id) 
                            INNER JOIN production_material pm on (pm.section_material_id = ps.id) 
                        WHERE 
                            so.id = %s 
                            """ % (tuple(having_values + [-1, -1])))
        seq = map(itemgetter(0), cr.fetchall())
        list_section = list(set(seq))
        return [('id', 'in', list_section)]

    def name_get(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = []
        if not ids:
            return res
        for record in self.browse(cr, uid, ids, context):
            order = record.plan_id and record.plan_id.sale_line_id and record.plan_id.sale_line_id.order_id and record.plan_id.sale_line_id.order_id.name or ''
            sale = record.plan_id and record.plan_id.sale_line_id and record.plan_id.sale_line_id.name or ''
            section = record.section_config_id and record.section_config_id.name or ''
            name = '[%s] - %s - %s ' % (order, sale, section)
            if record.stock_plan_id and record.stock_plan_id.name:
                name += ' - %s ' % record.stock_plan_id.name

            res.append((record.id, name))
        return res

    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'sequence': fields.integer('Sequence', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_id': fields.many2one('product.product', 'Product', required=True, readonly=True,
                                      states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'UoM'),
        'section_config_id': fields.many2one('init.section', 'Section Name', required=True, readonly=True,
                                             states={'draft': [('readonly', False)]}),
        'price': fields.float('Price Unit', readonly=True, states={'draft': [('readonly', False)]}),
        'norm': fields.float('Norm', readonly=True, states={'draft': [('readonly', False)]}),
        'stock_id': fields.function(_get_stock, string='Actual Factory', type='char', readonly=True),
        'stock_plan_id': fields.many2one('stock.warehouse', 'Plan Factory', required=True, readonly=True,
                                         states={'draft': [('readonly', False)]}),
        'qty': fields.function(_get_total_quantity, string='Qty(Kg)', type='float',
                               digits_compute=dp.get_precision('Product Unit of Measure'),
                               store={
                                   'production.section': (lambda self, cr, uid, ids, c={}: ids, ['finished_ids'], 10),
                                   'production.finished': (_get_order_finished, ['quantity'], 10),
                               },),
        'qty_kg': fields.function(_get_total_qty_kg, string='Qty(Yard)', type='float',
                                  digits_compute=dp.get_precision('Product Unit of Measure'),
                                  store={
                                      'production.section': (
                                      lambda self, cr, uid, ids, c={}: ids, ['finished_ids'], 10),
                                      'production.finished': (_get_order_finished, ['qty_kg'], 10),
                                  },),
        'total_qty_material': fields.function(_get_total_quantity_material, string='Quantity Material', type='float',
                                              digits_compute=dp.get_precision('Product Unit of Measure'),
                                              store={
                                                  'production.section': (
                                                  lambda self, cr, uid, ids, c={}: ids, ['material_ids'], 10),
                                                  'production.material': (_get_order_material, ['quantity'], 10),
                                              },),
        'user_id': fields.many2one('res.users', 'User Create', readonly=True, states={'draft': [('readonly', False)]}),
        'date_start': fields.date('Start Date', readonly=True, states={'draft': [('readonly', False)]}),
        'description': fields.text('Description', readonly=True, states={'draft': [('readonly', False)]}),
        'material_ids': fields.one2many('production.material', 'section_material_id', 'Production Material',
                                        readonly=True, states={'draft': [('readonly', False)]}),
        'finished_ids': fields.one2many('production.finished', 'section_finished_id', 'Production Finished',
                                        readonly=True, states={'draft': [('readonly', False)]}),
        'history_ids': fields.one2many('history.section', 'section_id', 'History Section'),
        'history_fact_ids': fields.one2many('history.factory', 'section_fact_id', 'History Factory'),
        'plan_id': fields.many2one('production.plan', 'Plan'),
        'type': fields.selection([('lifestyle', 'Deliveried Material from LifeStyle'),
                                  ('factory', 'Deliveried Material from Factory'),
                                  ('infactory', 'Incomming Material to Factory')], 'Description'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('confirm', 'Confirm'),
                                   ('cancel', 'Cancel'),
                                   ('done', 'Closed')], 'Status', readonly=True),
        'section_id': fields.many2one('production.section', 'Section', domain="[('plan_id', '=', plan_id)]"),
        'section_ids': fields.many2many('production.section', 'section_rel', 'section1_id', 'section2_id', 'Sections',
                                        domain="[('plan_id', '=', plan_id)]"),
        'sale_id': fields.function(_get_sale_id, method=True, type='many2one', fnct_search=_sale_search,
                                   relation='sale.order', string='Sale Order', store=True),
    }

    def set_to_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)


    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        ids = []
        if ids:
            ids = self.search(cr, user, [('name', '=', name)] + args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit)
        if not ids:
            ids = self.search(cr, user, [('plan_id.name', operator, name)] + args, limit=limit)
        return self.name_get(cr, user, ids, context)

    def _check_finish_product(self, cr, uid, ids, context={}):
        obj = self.browse(cr, uid, ids[0])
        if round(obj.qty) != round(obj.total_qty_material * obj.norm):
            return False
        return True

    #    _constraints = [
    #        (_check_finish_product, 'Error ! Quantity of finish product must be total quantity * norm. ', ['norm','material_ids','finished_ids']),
    #    ]

    def load_section(self, cr, uid, ids, context=None):
        return True

    def onchange_section_config_id(self, cr, uid, ids, section_config_id, context=None):
        if not section_config_id:
            return {}
        res = {}
        product = self.pool.get('init.section').browse(cr, uid, section_config_id, context=context)
        res['name'] = product.name or ''
        return {'value': res}

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        if not product_id:
            return {}
        res = {}
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        res['price'] = product.list_price or 0
        res['product_uom'] = product.uom_id and product.uom_id.id or False
        return {'value': res}

    def onchange_section_ids(self, cr, uid, ids, section_ids, sequence, plan_id, context=None):
        section_obj = self.pool.get('production.section')
        list = section_ids[0][2]
        list_old = section_obj.search(cr, uid,
                                      [('id', 'not in', ids), ('plan_id', '=', plan_id), ('sequence', '=', sequence)])
        res = {}
        if not list:
            res['material_ids'] = []
            return {'value': res}
        result = []
        result_old = []

        sections = section_obj.browse(cr, uid, list, context=context)
        sections_old = section_obj.browse(cr, uid, list_old, context=context)
        if sections:
            for section in sections:
                if section.finished_ids:
                    for f in section.finished_ids:
                        result.append({
                            'product_id': section.product_id and section.product_id.id or False,
                            'product_uom': section.product_id and (
                            section.product_id.uom_id and section.product_id.uom_id.id or False) or False,
                            'quantity': f.quantity or 0,
                            'qty_kg': f.qty_kg or 0,
                            'date_in': f.date_out or False,
                            'stock_plan_id': section.stock_plan_id and section.stock_plan_id.id or False,
                            'material_of_section_id': section.id,
                            'product_custom_id' : f.product_custom_id and f.product_custom_id.id or False,
                            'color_id' : f.color_id and f.color_id.id or False,
                        })
        if sections_old:
            for section_old in sections_old:
                if section_old.material_ids:
                    for f in section_old.material_ids:
                        result_old.append({
                            'product_id': f.product_id and f.product_id.id or False,
                            'product_uom': f.product_id and (
                            f.product_id.uom_id and f.product_id.uom_id.id or False) or False,
                            'quantity': f.quantity or 0,
                            'qty_kg': f.qty_kg or 0,
                            'date_in': f.date_in or False,
                            'stock_plan_id': f.stock_plan_id and f.stock_plan_id.id or False,
                            'material_of_section_id': section_old.id,
                            'product_custom_id' : f.product_custom_id and f.product_custom_id.id or False,
                            'color_id' : f.color_id and f.color_id.id or False,
                        })
        if result and result_old:
            quantity = 0
            qty_kg = 0
            for kq in result:
                qty_kg = kq['qty_kg']
                quantity = kq['quantity']
                for kq_old in result_old:
                    if kq['product_id'] == kq_old['product_id'] and kq['product_uom'] == kq_old['product_uom'] and kq[
                        'date_in'] == kq_old['date_in'] and kq['stock_plan_id'] == kq_old['stock_plan_id']:
                        qty_kg -= kq_old['qty_kg']
                        quantity -= kq_old['quantity']
                kq['qty_kg'] = qty_kg
                kq['quantity'] = quantity
        res['material_ids'] = result
        return {'value': res}

    def out_finished(self, cr, uid, ids, context=None):
        return {'name': 'Delivery Material Previous',
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'create.out.material.pre.wizard',
                'res_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'context': context,
                'target': 'new',
                'domain': '[]',
        }

    def out_material(self, cr, uid, ids, context=None):
        return {'name': 'Delivery Material',
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'create.out.material.wizard',
                'res_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'context': context,
                'target': 'new',
                'domain': '[]',
        }

    def in_finished(self, cr, uid, ids, context=None):
        return {'name': 'Incoming Finished',
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'create.in.finished.wizard',
                'res_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'context': context,
                'target': 'new',
                'domain': '[]',
        }

    _defaults = {
        'state': lambda *a: 'draft',
        'user_id': lambda self, cr, uid, context: uid,
    }


class production_material(osv.osv):
    _name = 'production.material'
    _inherit = ['mail.thread']

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'quantity': fields.float('Qty(Kg)', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'qty_kg': fields.float('Qty(Yard)', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'UoM'),
        'date_in': fields.date('Date In'),
        'qty_out': fields.float('Out Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),),
        'qty_out2': fields.float('Out Quantity from Factory',
                                 digits_compute=dp.get_precision('Product Unit of Measure'),),
        'qty_kg_out': fields.float('Out Qty(kg)', digits_compute=dp.get_precision('Product Unit of Measure'),),
        'qty_kg_out2': fields.float('Out Qty(kg) from Factory',
                                    digits_compute=dp.get_precision('Product Unit of Measure'),),
        'section_material_id': fields.many2one('production.section', 'Section'),
        'section_id': fields.many2one('production.section', 'Section'),
        'stock_plan_id': fields.many2one('stock.warehouse', 'Plan Factory'),
        'material_of_section_id': fields.many2one('production.section', 'Section'),
        'partner_id': fields.many2one('res.partner', 'Supplier'),
        'price_unit': fields.float('Price Unit(Buy Material)'),
        'product_custom_id': fields.many2one('product.custom', 'Custom'),
        'color_id': fields.many2one('product.color', 'Color'),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        if not product_id:
            return {}
        res = {}
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        res['product_uom'] = product.uom_id and product.uom_id.id or False
        return {'value': res}

    #    def onchange_section_id(self, cr, uid, ids, section_id, context=None):
    #        if not section_id:
    #            return {}
    #        res = {}
    #        section = self.pool.get('production.section').browse(cr, uid, section_id, context=context)
    #        cr.execute("""SELECT MAX(p_f.date_out) AS max_date
    #                FROM production_finished p_f
    #                LEFT JOIN  production_section p_s ON (p_s.id = p_f.section_finished_id)
    #                    WHERE p_s.id = '%s' """ %(section_id))
    #        date_in = cr.fetchone()
    #        res['product_id'] = section.product_id and section.product_id.id or False
    #        res['quantity'] = section.qty or 0
    #        res['date_in']= date_in[0]
    #        return {'value': res}

    _defaults = {
    }


class production_finished(osv.osv):
    _name = 'production.finished'
    _inherit = ['mail.thread']
    _columns = {
        'name': fields.char('Name', size=256),
        'date_finished': fields.date('Date Finished'),
        'quantity': fields.float('Qty(Kg)', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'qty_kg': fields.float('Qty(Yrd)', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'qty_out3': fields.float('Incomming Finished Product',
                                 digits_compute=dp.get_precision('Product Unit of Measure'),),
        'qty_kg_out3': fields.float('Incomming (Qty(kg)) Finished Product',
                                    digits_compute=dp.get_precision('Product Unit of Measure'),),
        'product_uom': fields.many2one('product.uom', 'UoM'),
        'date_out': fields.date('Date Out'),
        'section_finished_id': fields.many2one('production.section', 'Section'),
        'product_custom_id': fields.many2one('product.custom', 'Custom'),
        'color_id': fields.many2one('product.color', 'Color'),
    }
    _defaults = {
    }


class history_section(osv.osv):
    _name = "history.section"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'quantity': fields.float('Qty(Kg)'),
        'user_id': fields.many2one('res.users', 'User Out'),
        #        'des': fields.char('Description', size=256),
        'des': fields.selection(
            [('lifestyle', 'Deliveried Material from LifeStyle'), ('factory', 'Deliveried Material from Factory'),
             ('infactory', 'Incomming Product finished to Factory')], 'Description'),
        'date_out': fields.date('Date Out'),
        'location_id': fields.many2one('stock.location', 'Location'),
        'location_dest_id': fields.many2one('stock.location', 'Dest Location'),
        'section_id': fields.many2one('production.section', 'Section'),
    }
    _defaults = {
    }


class history_factory(osv.osv):
    _name = "history.factory"
    _columns = {
        'stock_id': fields.many2one('stock.warehouse', 'Factory'),
        'section_fact_id': fields.many2one('production.section', 'Section'),
        'in_material_ids': fields.one2many('history.factory.detail', 'factory_id', 'Incoming Material',
                                           domain=[('type', '=', 'in_material')]),
        'out_material_ids': fields.one2many('history.factory.detail', 'factory_id', 'Delivery Material',
                                            domain=[('type', '=', 'out_material')]),
        'in_finished_ids': fields.one2many('history.factory.detail', 'factory_id', 'Incoming Finished',
                                           domain=[('type', '=', 'in_finished')]),
        'out_finished_ids': fields.one2many('history.factory.detail', 'factory_id', 'Delivery Finished',
                                            domain=[('type', '=', 'out_finished')]),
    }
    _defaults = {
    }


class history_factory_detail(osv.osv):
    _name = "history.factory.detail"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'factory_id': fields.many2one('history.factory', 'Factory'),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'qty_kg': fields.float('Qty(kg)', digits_compute=dp.get_precision('Product Unit of Measure')),
        'price_unit': fields.float('Price Unit'),
        'date': fields.date('Date'),
        'user_id': fields.many2one('res.users', 'User'),
        'move_id': fields.many2one('stock.move', 'Move'),
        'type': fields.selection([('in_material', 'Incoming Material'), ('out_material', 'Delivery Material'),
                                  ('in_finished', 'Incomming Finished'), ('out_finished', 'Delivery Finished')],
                                 'Type'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'roll': fields.char('Roll', size=256),
    }
    _defaults = {
    }                 


class product_custom(osv.osv):
    _name = "product.custom"
    _columns = {
        'name': fields.char('Name', size=256),
    }
    
