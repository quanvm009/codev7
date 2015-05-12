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

from openerp import tools
from openerp.osv import fields, osv


class plan_report(osv.osv):
    _name = "plan.report"
    _description = "Plan Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date Order', readonly=True),
        'date_confirm': fields.date('Date Confirm', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month': fields.selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                                   ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
                                   ('10', 'October'), ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', readonly=True),
        'product_uom_qty': fields.float('# of Qty', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'section_id': fields.many2one('production.section', 'Section', readonly=True),
        'plan_id': fields.many2one('production.plan', 'Plan', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'finish_qty_section': fields.float('Finish Qty Section', readonly=True),
        'recieve_finish_qty': fields.float('Recieve Qty Finished', readonly=True),
        'sale_id': fields.many2one('sale.order', 'Sale Order', readonly=True),
        'state': fields.selection([
                                      ('draft', 'Quotation'),
                                      ('waiting_date', 'Waiting Schedule'),
                                      ('manual', 'Manual In Progress'),
                                      ('progress', 'In Progress'),
                                      ('invoice_except', 'Invoice Exception'),
                                      ('done', 'Done'),
                                      ('cancel', 'Cancelled')
                                  ], 'Order Status', readonly=True),
        'price_unit': fields.float('Price Unit', digits=(16, 2), readonly=True),
    }
    _order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'plan_report')
        cr.execute("""
            create or replace view plan_report as (
                
                select ROW_NUMBER() OVER(ORDER BY sale_id DESC) AS id,
                sale_id, plan_id, tbl1.section_id, tbl1.product_id, finish_qty_section,recieve_finish_qty,
                date,
                to_char(date, 'YYYY') as year,
                to_char(date, 'MM') as month,
                to_char(date, 'YYYY-MM-DD') as day,
                partner_id,
                user_id,
                product_uom_qty,
                price_unit
                from
                (select s.id as sale_id, pl.id as plan_id,ps.id as section_id, ps.product_id, 
                    sum(qty) as finish_qty_section,s.date_order as date,s.partner_id as partner_id,
                    pl.user_id as user_id,ps.qty as product_uom_qty,ps.price as price_unit
                        
                from sale_order s
                    inner join sale_order_line l on l.order_id=s.id
                    inner join production_plan pl on pl.sale_line_id=l.id
                    inner join production_section ps on  ps.plan_id= pl.id

                group by
                            s.id,    
                            pl.id,    
                            ps.id,     
                            ps.product_id,
                            s.partner_id,
                            s.date_order,
                            pl.user_id,
                            ps.qty,
                            ps.price) as tbl1 left join 
                
             (select sm.product_id ,sm.section_id , sum(sm.product_qty) as recieve_finish_qty from stock_move sm
                where sm.section_id in (select ps.id from sale_order s
                inner join sale_order_line l on l.order_id=s.id
                inner join production_plan pl on pl.sale_line_id=l.id
                inner join production_section ps on  ps.plan_id= pl.id) and sm.state = 'done'
                group by sm.product_id,sm.section_id) as tbl2 on tbl2.section_id = tbl1.section_id and tbl2.product_id = tbl1.product_id

                    
              
            )
        """)


plan_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
