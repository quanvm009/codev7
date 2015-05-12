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


class wizard_init_order(osv.osv_memory):
    _name = "wizard.init.order"
    _columns = {
        'month_to': fields.date('Date To', required=True),
        'month_from': fields.date('Date From', required=True),
    }
    _defaults = {
        'month_from': lambda *a: time.strftime('%Y-%m-01'),
        'month_to': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def onchange_month(self, cr, uid, ids, month_to, month_from):
        if month_from and month_to:
            if month_to < month_from:
                raise osv.except_osv('error', 'error')
        return {}

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}

        res = self.read(cr, uid, ids, ['month_to', 'month_from'],
                        context=context)
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'wizard.init.order'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'report_order',
            'datas': datas,
        }


wizard_init_order()



