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


class sale_report(osv.osv):
    _name = "sale.report"
    _description = "Sales Orders Statistics"
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
        'qty_kg': fields.float('# of Qty(kg)', readonly=True),
        'color_id': fields.many2one('product.color', 'Color', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'sale_id': fields.many2one('sale.order', 'Sale Order', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'price_unit': fields.float('Price Unit', readonly=True),
        'plan_total': fields.float('Total Plan', readonly=True),
        'expense_total': fields.float('Total Expense', readonly=True),
        'revence_total': fields.float('Total Revence', readonly=True),
        'categ_id': fields.many2one('product.category', 'Category of Product', readonly=True),
        'state': fields.selection([
                                      ('draft', 'Quotation'),
                                      ('waiting_date', 'Waiting Schedule'),
                                      ('manual', 'Manual In Progress'),
                                      ('progress', 'In Progress'),
                                      ('invoice_except', 'Invoice Exception'),
                                      ('done', 'Done'),
                                      ('cancel', 'Cancelled')
                                  ], 'Order Status', readonly=True),
    }
    _order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_report')
        cr.execute("""
            create or replace view sale_report as (
                select min(sol.id) as id,
                    s.id as sale_id, 
                ( select (case when i.type = 'out_invoice' then sum(price_subtotal)
                 when i.type = 'out_refund' then sum(-price_subtotal)
                else 0 end)
                    from account_invoice_line l
                    left join account_invoice i
                        on i.id = l.invoice_id
                    where l.sale_id = s.id and l.product_id = sol.product_id
            and i.state not in ('draft','cancel')
                        and i.type in ('out_invoice','out_refund')
                    group by i.type)/(select count(id) from sale_order_line where order_id = s.id and product_id = sol.product_id) 
                    as revence_total, 
                sol.product_id as product_id, 
               ( select (case when i.type = 'in_invoice' then sum(price_subtotal)
                 when i.type = 'in_refund' then sum(-price_subtotal)
                else 0 end)
                    from account_invoice_line l
                    left join account_invoice i
                        on i.id = l.invoice_id
                    where l.sale_id = s.id and l.product_id = sol.product_id
            and i.state not in ('draft','cancel')
                        and i.type in ('in_invoice','in_refund')
                    group by i.type) /(select count(id) from sale_order_line where order_id = s.id and product_id = sol.product_id)
                    as expense_total,
                s.date_order as date,
                to_char(s.date_order, 'YYYY') as year,
                to_char(s.date_order, 'MM') as month,
                to_char(s.date_order, 'YYYY-MM-DD') as day,
                s.partner_id as partner_id,
                s.user_id as user_id ,
                pc.id as color_id,
                t.uom_id as product_uom,sum(sol.product_uom_qty / u.factor * u2.factor) as product_uom_qty
                ,sum(sol.qty_kg / u.factor * u2.factor) as qty_kg,sum(sol.product_uom_qty),sum(s.amount_total) as plan_total
                from
                    sale_order_line sol                         
                    left join sale_order s
                        on s.id = sol.order_id
                    join product_product p 
                        on (sol.product_id=p.id)
                    join product_template t 
                        on (p.product_tmpl_id=t.id)
                    join product_uom u 
                        on (u.id=sol.product_uom)
                    join product_uom u2 
                        on (u2.id=t.uom_id)
                    left join product_color pc 
                        on (pc.id=sol.color_id)
                    
                group by s.id,sol.product_id,s.partner_id,s.user_id,s.date_order,pc.id,t.uom_id
                    
            )
        """)


sale_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
