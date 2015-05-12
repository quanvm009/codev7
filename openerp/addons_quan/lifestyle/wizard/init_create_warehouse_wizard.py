# -*- coding: utf-8 -*-
# #############################################################################
#
#    INIT TECH, Open Source Management Solution
#    Copyright (C) 2012-2013 Tiny SPRL (<http://init.vn>).
#
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _


class init_creat_warehouse_wizard(osv.osv_memory):
    _name = "init.create.warehouse.wizard"

    _columns = {
        'name': fields.char('Factory', 64, required=True),
    }

    def action_create_warehouse(self, cr, uid, ids, context=None):
        warehouse_obj = self.pool.get('stock.warehouse')
        location_obj = self.pool.get('stock.location')
        warehouse_ids = []
        for vals in self.browse(cr, uid, ids, context=context):
            # create location
            location_id = warehouse_obj._default_lot_input_stock_id(cr, uid, context)
            location_id = location_obj.copy(cr, uid, location_id, {'name': vals.name}, context=context)
            # create warehouse
            partner_id = self.pool.get('res.partner').create(cr, uid, {'name': vals.name,
                                                                       'customer': False,
                                                                       'supplier': True})
            warehouse_id = warehouse_obj.create(cr, uid, {
                'name': vals.name,
                'partner_id': partner_id,
                'lot_input_id': location_id,
                'lot_stock_id': location_id,
            })
            warehouse_ids.append(warehouse_id)
        return {
            'name': _('Warehouses'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.warehouse',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': warehouse_ids and warehouse_ids[0] or False,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
