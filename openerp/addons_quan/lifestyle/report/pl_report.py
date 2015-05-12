from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
import random
from openerp.osv import fields, osv
import time
from  openerp import pooler


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            '_get_sale_order': self._get_sale_order,
            '_get_balance_qty': self._get_balance_qty,
            '_get_warehouse': self._get_warehouse,
            'check': self.check,
        })
        self.context = context

    def _get_sale_order(self, data):
        if data['sale_order_id'] == []:
            sql = """
                select so.id,so.name from sale_order so
                LEFT JOIN  sale_order_line sol on so.id= sol.order_id
                LEFT JOIN stock_move sm on sm.sale_line_id= sol.id
                where so.state not in ('draft','cancel') and  sm.date <'%s' and sm.date>'%s'
                group by so.id,so.name """ % (data['month_to'], data['month_from'])
        else:
            if len(data['sale_order_id']) == 1:
                data['sale_order_id'].append(-1)
            sql = """
                    select so.id,so.name from sale_order so
                    LEFT JOIN  sale_order_line sol on so.id= sol.order_id
                    LEFT JOIN stock_move sm on sm.sale_line_id= sol.id
                    where so.state not in ('draft','cancel') and  sm.date <'%s' and sm.date>'%s' and so.id in %s
                    group by so.id,so.name """ % (data['month_to'], data['month_from'], tuple(data['sale_order_id']))
        self.cr.execute(sql)
        res = self.cr.dictfetchall()
        return res

    def _get_warehouse(self, data):
        if data['warehouse_id'] == []:
            sql = """
                    select sw.id,sw.name from stock_warehouse sw
                    LEFT JOIN stock_location sl on sl.id = sw.lot_stock_id 
                    LEFT JOIN stock_move sm on sl.id = sm.location_id 
                    where sm.date <'%s' and sm.date>'%s'
                    group by sw.id,sw.name """ % (data['month_to'], data['month_from'])
        else:
            if len(data['warehouse_id']) == 1:
                data['warehouse_id'].append(-1)
            sql = """
                        select sw.id,sw.name from stock_warehouse sw
                        LEFT JOIN stock_location sl on sl.id = sw.lot_stock_id 
                        LEFT JOIN stock_move sm on sl.id = sm.location_id 
                        where sm.date <'%s' and sm.date>'%s' and sw.id in %s
                        group by sw.id,sw.name """ % (data['month_to'], data['month_from'], tuple(data['warehouse_id']))
        self.cr.execute(sql)
        res = self.cr.dictfetchall()
        return res

    def _get_balance_qty(self, data, sale_order, warehouse):
        date_to = data['month_to']
        date_from = data['month_from']
        sql = """
                   with tblnhap as
               (
                   select coalesce(sm.color_id,0) as color, sm.product_id as product_id , date, sm.product_qty as nhap, so.id as DH, sol.id as SOL from 
                   stock_move sm,stock_location sl, sale_order so, sale_order_line sol,stock_warehouse sw
                   where sm.location_dest_id = sl.id and sm.sale_line_id = sol.id and sol.order_id = so.id and sl.id = sw.lot_stock_id 
                   and usage like 'internal' and sw.id = %s and so.id = %s and sm.state = 'done' 
               ) 
               , tblxuat as
               (
                   select coalesce(sm.color_id,0) as color, sm.product_id as product_id, date, sm.product_qty as xuat,so.id as DH, sol.id as SOL from 
                   stock_move sm, stock_location sl, sale_order so, sale_order_line sol,stock_warehouse sw
                   where sm.location_id = sl.id  and sm.sale_line_id = sol.id and sol.order_id = so.id and sl.id = sw.lot_stock_id 
                   and usage like 'internal' and sw.id = %s and so.id = %s and sm.state = 'done'
                ),
                
               tblnhapdauky as
               (
                   select tblnhap.product_id as product_id,DH,color,SOL,
                   SUM(tblnhap.nhap) as nhapdauky
                   from tblnhap
                   where tblnhap.date <='%s'
                   group by tblnhap.product_id,DH,color,SOL
               ),
               tblnhaptrongky as
              (
              select tblnhap.product_id as product_id,DH,color,SOL,
                  SUM(tblnhap.nhap)
                  as nhaptrongky 
                     from tblnhap
                     where tblnhap.date between '%s' and '%s'
                     group by tblnhap.product_id,DH,color,SOL
                 ),
                 tblxuatdauky as
                 (
                     select tblxuat.product_id product_id, DH,color,SOL,
                     sum (tblxuat.xuat) as xuatdauky
                     from tblxuat
                     where tblxuat.date<='%s'
                     group by tblxuat.product_id, DH,color,SOL
                 ),
                 tblxuattrongky as
                 (
                     select tblxuat.product_id as product_id, DH,color,SOL,
                      SUM(tblxuat.xuat)
                     as xuattrongky
                     from tblxuat
                     where tblxuat.date between '%s' and '%s'
                     group by tblxuat.product_id, DH,color,SOL
                 ),
                 tblnhapcuoiky as
                 (
                   select tblnhap.product_id as product_id,DH,color,SOL,
                   SUM(tblnhap.nhap) as nhapcuoiky
                   from tblnhap
                   where tblnhap.date <='%s'
                   group by tblnhap.product_id,DH,color,SOL
                 ),
                 tblxuatcuoiky as
                 (
                   select tblxuat.product_id as product_id,DH,color,SOL,
                   SUM(tblxuat.xuat) as xuatcuoiky
                   from tblxuat
                   where tblxuat.date <='%s'
                   group by tblxuat.product_id,DH,color,SOL
                 ),
                 tblstock_move as
                 (select origin, sale_line_id , coalesce(color_id,0) as color_id, product_id from stock_move),
                 tblketquatamthoi as
                (
                 select sm.product_id as product_id,sm.color_id as color,
                 (case 
                 when tblnhapdauky.nhapdauky Is null then 0
                 else tblnhapdauky.nhapdauky end) as nhapdauky
                 ,
                 (case 
                 when tblxuatdauky.xuatdauky IS null then 0
                 else tblxuatdauky.xuatdauky end) as xuatdauky
                 ,
                 (case 
                 when tblnhaptrongky.nhaptrongky IS null then 0
                 else tblnhaptrongky.nhaptrongky end) as nhaptrongky
                 ,
                 (case 
                 when tblxuattrongky.xuattrongky IS null then 0
                 else tblxuattrongky.xuattrongky end) as xuattrongky,
                 (case
                 when tblnhapcuoiky.nhapcuoiky IS null then 0
                 else tblnhapcuoiky.nhapcuoiky end
                 ) as nhapcuoiky,
                 (case
                 when tblxuatcuoiky.xuatcuoiky IS null then 0
                 else tblxuatcuoiky.xuatcuoiky end
                 ) as xuatcuoiky
           
                 
                 from tblstock_move sm left join tblnhapdauky on (sm.sale_line_id = tblnhapdauky.SOL  and sm.color_id = tblnhapdauky.color and sm.product_id = tblnhapdauky.product_id)
                 left join tblxuatdauky on (sm.sale_line_id = tblxuatdauky.SOL  and sm.color_id = tblxuatdauky.color and sm.product_id = tblxuatdauky.product_id)
                 left join tblnhaptrongky on (sm.sale_line_id = tblnhaptrongky.SOL and sm.product_id = tblnhaptrongky.product_id  and sm.color_id = tblnhaptrongky.color )
                 left join tblxuattrongky on (sm.sale_line_id = tblxuattrongky.SOL and sm.color_id = tblxuattrongky.color and sm.product_id = tblxuattrongky.product_id)
                 left join tblnhapcuoiky on (sm.sale_line_id = tblnhapcuoiky.SOL  and sm.color_id = tblnhapcuoiky.color and sm.product_id = tblnhapcuoiky.product_id)
                 left join tblxuatcuoiky on (sm.sale_line_id = tblxuatcuoiky.SOL  and sm.color_id = tblxuatcuoiky.color and sm.product_id = tblxuatcuoiky.product_id)),
                
                 
                 tblketqua as(
                 select DISTINCT pp.name_template as product, pc.name as color,nhapdauky-xuatdauky as tondauky,
                 nhaptrongky,xuattrongky, nhapcuoiky-xuatcuoiky as toncuoiky 
                 from tblketquatamthoi kqtt left join product_product pp on kqtt.product_id = pp.id
                 left join product_color pc on kqtt.color = pc.id
                 where ( nhapdauky-xuatdauky >0 or nhaptrongky>0 or xuattrongky >0 or (nhapdauky-xuatdauky)+(nhaptrongky-xuattrongky) >0))

                 select  ROW_NUMBER() OVER(ORDER BY product DESC) AS STT, product, color, tondauky, nhaptrongky, xuattrongky, toncuoiky from tblketqua 
              """ % (
        warehouse, sale_order, warehouse, sale_order, date_from, date_from, date_to, date_from, date_from, date_to,
        date_to, date_to )
        self.cr.execute(sql)
        res = self.cr.dictfetchall()
        return res

    def check(self, data, sale_order, warehouse):
        res = self._get_balance_qty(data, sale_order, warehouse)
        if len(res) >= 1:
            return 'A'
        return 'B'
    
