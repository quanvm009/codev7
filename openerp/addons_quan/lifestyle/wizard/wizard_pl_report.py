# -*- encoding: utf-8 -*-
# #############################################################################
#
#    General Solutions, Open Source Management Solution
#    Copyright (C) 2009 General Solutions (<http://generalsolutions.vn>). All Rights Reserved
#
##############################################################################
import time
import tools
import base64
import cStringIO
import csv
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from operator import itemgetter


class wizard_init_stock_movement(osv.osv_memory):
    _name = "wizard.init.stock.movement"

    def _get_warehouse_id(self, cr, uid, context=None):
        lst_warehouse = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)

        return lst_warehouse

    _columns = {
        'warehouse_id': fields.many2many('stock.warehouse', 'warehouse_rel_move', 'warehouse_id', 'move_id',
                                         'Warehouse', required=True),
        'month_to': fields.date('Date To', required=True),
        'month_from': fields.date('Date From', required=True),
        'sale_order_id': fields.many2many('sale.order', 'order_rel_move', 'order_id', 'move_id', domain=[('state','not in',['draft','cancel'])]),
    }
    _defaults = {
        'warehouse_id': _get_warehouse_id,
        'month_from': lambda *a: time.strftime('%Y-%m-01'),
        'month_to': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def onchange_sale_order_id(self, cr, uid, ids, sale_order_id, context=None):
        if not sale_order_id:
            return {'value': {}}
        list_warehouse = []
        list_sale_id = sale_order_id[0][2]
        cr.execute("""SELECT hf.stock_id
                        FROM production_section ps
                            INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                            INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id) 
                            INNER JOIN sale_order so on (sol.order_id = so.id) 
                            INNER JOIN history_factory hf on (ps.id = hf.section_fact_id) 
                        WHERE 
                            so.id in %s
                            """ % str(tuple(list_sale_id + [-1, -1])))

        seq = map(itemgetter(0), cr.fetchall())
        list_warehouse = list(set(seq))
        val = {
            'warehouse_id': list_warehouse,
        }
        return {'value': val}


    def onchange_month(self, cr, uid, ids, month_to, month_from):
        if month_from and month_to:
            if month_to < month_from:
                raise osv.except_osv('error', 'error')
        return {}

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}

        res = self.read(cr, uid, ids, ['warehouse_id', 'month_to', 'month_from', 'sale_order_id'],
                        context=context)
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'wizard.init.stock.movement'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'sm_report_location',
            'datas': datas,
        }


wizard_init_stock_movement()



