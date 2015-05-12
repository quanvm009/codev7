from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
import random
from openerp.osv import fields, osv
import time
from openerp import pooler
from operator import itemgetter


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'list_user': self.get_list_user,
            'list_order': self.get_list_order,
            'qty_price_move': self.get_qty_price_move,
            'sum_qty_user': self.sum_qty_user,
            'total': self.total,
        })
        self.context = context

    def get_list_user(self):
        result = []
        ids_order = self.pool.get('sale.order').search(self.cr, self.uid, [])
        obj_order = ids_order and self.pool.get('sale.order').browse(self.cr, self.uid, ids_order) or []
        ids_user = list(set([order.user_id and order.user_id.id for order in obj_order]))
        obj_user = self.pool.get('res.users').browse(self.cr, self.uid, ids_user)
        for user in obj_user:
            result.append({
                'id': user.id or False,
                'name': user.name or False
            })
        return result

    def get_list_order(self, data, user):
        result = []
        ids_order = self.pool.get('sale.order').search(self.cr, self.uid, [('date_order', '<=', data['month_to']),
                                                                           ('date_order', '>=', data['month_from']),
                                                                           ('user_id', '=', user)])
        obj_order = ids_order and self.pool.get('sale.order').browse(self.cr, self.uid, ids_order) or []
        cur_obj = self.pool.get('res.currency')
        stt = 0
        for order in obj_order:
            company_currency = self.pool['res.company'].browse(self.cr, self.uid, order.company_id.id).currency_id.id
            qty_yard = 0
            qty_kg = 0
            for line in order.order_line:
                qty_yard += line.product_uom_qty or 0
                qty_kg += line.qty_kg or 0
            stt += 1
            result.append({
                'stt': stt,
                'id': order.id or False,
                'name': order.name or False,
                'partner': order.partner_id and order.partner_id.name or '',
                'lc': order.lc or '',
                'qty_yard': qty_yard or 0,
                'qty_kg': qty_kg or 0,
                'price_nt': order.amount_total,
                'date_order': order.date_order,
                'price': cur_obj.compute(self.cr, self.uid, order.currency_id.id, company_currency, order.amount_total,
                                         context={'date': order.date_order or time.strftime('%Y-%m-%d')}, round=False)
            })
        stt = 0
        return result

    def get_qty_price_move(self, sale_id):
        qty_yard = 0
        amount_total = 0
        price = 0
        ids_picking = self.pool.get('stock.picking').search(self.cr, self.uid,
                                                            [('sale_id', '=', sale_id), ('state', '=', 'done')])
        picking = ids_picking and self.pool.get('stock.picking').browse(self.cr, self.uid, ids_picking[0]) or False
        date_done = picking and picking.date_done or ''
        cur_obj = self.pool.get('res.currency')
        order = self.pool.get('sale.order').browse(self.cr, self.uid, sale_id)
        company_currency = self.pool['res.company'].browse(self.cr, self.uid, order.company_id.id).currency_id.id
        if picking:
            for move in picking.move_lines:
                if move.sale_line_id.id:
                    price_unit = self.pool.get('sale.order.line').browse(self.cr, self.uid,
                                                                         move.sale_line_id.id).price_unit or 0
                    qty_yard += move.product_qty or 0
                    amount_total += move.product_qty * price_unit or 0
                    price = cur_obj.compute(self.cr, self.uid, order.currency_id.id, company_currency, amount_total,
                                            context={'date': order.date_order or time.strftime('%Y-%m-%d')},
                                            round=False)
        return [qty_yard, amount_total, price, date_done]


    def sum_qty_user(self, data, user):
        sum_qty_yard = 0
        sum_price_nt = 0
        sum_qty_yard_tt = 0
        sum_price_nt_tt = 0
        sum_price_company = 0
        sum_price_company_tt = 0
        sum_qty_kg = 0
        for line in self.get_list_order(data, user):
            sum_qty_yard += line['qty_yard']
            sum_price_nt += line['price_nt']
            sum_price_company += line['price']
            sum_qty_yard_tt += self.get_qty_price_move(line['id'])[0]
            sum_price_nt_tt += self.get_qty_price_move(line['id'])[1]
            sum_price_company_tt += self.get_qty_price_move(line['id'])[2]
            sum_qty_kg += line['qty_kg']
        return [sum_qty_yard, sum_price_nt, sum_price_company, sum_qty_yard_tt, sum_price_nt_tt, sum_price_company_tt,
                sum_qty_kg]

    def total(self, data):
        total_qty_yard = 0
        total_price_nt = 0
        total_price_company = 0
        total_qty_yard_tt = 0
        total_price_nt_tt = 0
        total_price_company_tt = 0
        total_qty_kg = 0
        for user in self.get_list_user():
            total_qty_yard += self.sum_qty_user(data, user['id'])[0]
            total_price_nt += self.sum_qty_user(data, user['id'])[1]
            total_price_company += self.sum_qty_user(data, user['id'])[2]
            total_qty_yard_tt += self.sum_qty_user(data, user['id'])[3]
            total_price_nt_tt += self.sum_qty_user(data, user['id'])[4]
            total_price_company_tt += self.sum_qty_user(data, user['id'])[5]
            total_qty_kg += self.sum_qty_user(data, user['id'])[6]
        return [total_qty_yard, total_price_nt, total_price_company, total_qty_yard_tt, total_price_nt_tt,
                total_price_company_tt, total_qty_kg]
        
