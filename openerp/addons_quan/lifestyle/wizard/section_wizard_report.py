# -*- coding: utf-8 -*-
# #############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

from openerp.osv import fields, osv


class section_wizard_report(osv.osv_memory):
    _name = 'section.wizard.report'
    _description = 'Section Wizard Report'
    _columns = {
        'sale_id': fields.many2one('sale.order', string='Sale Order', domain=[('state', '!=', 'cancel')],
                                   required=True),
        'section_id': fields.many2one('init.section', string='Section', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', string='Factory'),
    }

    def onchange_sale_id(self, cr, uid, ids, sale_id, context=None):
        if context is None:
            context = {}
        res = {}
        list_warehouse = []
        list_section = []
        list_section1 = []

        cr.execute("""SELECT ps.section_config_id
                        FROM production_section ps
                            INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                            INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id) 
                            INNER JOIN sale_order so on (sol.order_id = so.id) 
                        WHERE 
                            so.id = %s
                            """ % (sale_id))
        seq1 = map(itemgetter(0), cr.fetchall())
        list_section = list(set(seq1))

        cr.execute("""SELECT hf.stock_id
                        FROM production_section ps
                            INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                            INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id) 
                            INNER JOIN sale_order so on (sol.order_id = so.id) 
                            INNER JOIN history_factory hf on (ps.id = hf.section_fact_id) 
                        WHERE 
                            so.id = %s
                            """ % (sale_id))
        seq = map(itemgetter(0), cr.fetchall())
        list_warehouse = list(set(seq))
        #### lay section cuoi cung
        cr.execute("""SELECT ps.section_config_id
                        FROM production_section ps
                            INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                            INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id) 
                            INNER JOIN sale_order so on (sol.order_id = so.id) 
                        WHERE 
                            so.id = %s and 
                            ps.sequence = (SELECT MAX(ps.sequence)
                                                FROM production_section ps
                                                    INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                                                    INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id) 
                                                    INNER JOIN sale_order so on (sol.order_id = so.id) 
                                                WHERE so.id = %s
                                                )
                            """ % (sale_id, sale_id))
        seq2 = map(itemgetter(0), cr.fetchall())
        list_section1 = list(set(seq2))

        res['section_id'] = list_section1 and list_section1[0] or False

        return {'domain': {'warehouse_id': [('id', 'in', list_warehouse)],
                           'section_id': [('id', 'in', list_section)]},
                'value': res
        }

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}

        res = self.read(cr, uid, ids, ['sale_id', 'section_id', 'warehouse_id'], context=context)
        res = res and res[0] or {}
        datas['form'] = res
        datas['model'] = 'section.wizard.report'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'warehouse_section',
            'datas': datas,
        }


section_wizard_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
