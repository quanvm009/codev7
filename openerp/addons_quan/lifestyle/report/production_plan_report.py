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
        self.stt = 0
        self.localcontext.update({
            'time': time,
            'get_stt': self.get_stt,
            'get_list_factory': self.get_list_factory,
            'get_list_finished': self.get_list_finished,
            'get_list_material': self.get_list_material,
            'sum_qty_material': self.sum_qty_material,
            'sum_qty_finished': self.sum_qty_finished,
            'sum_total_qty_material': self.sum_total_qty_material,
            'sum_total_qty_finished': self.sum_total_qty_finished,
        })
        self.context = context

    def get_stt(self):
        stt = self.stt + 1
        return stt

    def get_list_factory(self, plan):
        result = []
        for line in plan.section_ids:
            dic = {
                'id': line.stock_plan_id.id or False,
                'name': line.stock_plan_id.name or '',
            }
            result.append(dic)
        return result

    def get_list_finished(self, plan, fact):
        result = []
        if plan.section_ids:
            for line in plan.section_ids:
                if line.stock_plan_id.id == fact['id'] and line.finished_ids:
                    for fin in line.finished_ids:
                        dic = {
                            'name': line.product_id and line.product_id.name or False,
                            'quantity': fin.quantity or 0,
                            'date_out': fin.date_out,
                        }
                        result.append(dic)
        return result

    def get_list_material(self, plan, fact):
        result = []
        if plan.section_ids:
            for line in plan.section_ids:
                if line.stock_plan_id.id == fact['id'] and line.material_ids:
                    for mat in line.material_ids:
                        dic = {
                            'name': mat.product_id and mat.product_id.name or False,
                            'quantity': mat.quantity or 0,
                            'date_in': mat.date_in,
                        }
                        result.append(dic)
        return result

    # viet ham tinh tong

    def sum_qty_material(self, plan, fact):
        sum_qty = 0
        for line in self.get_list_material(plan, fact):
            sum_qty += line['quantity']
        return sum_qty

    def sum_qty_finished(self, plan, fact):
        sum_qty = 0
        for line in self.get_list_finished(plan, fact):
            sum_qty += line['quantity']
        return sum_qty

    def sum_total_qty_material(self, plan):
        total_qty = 0
        for line in plan.section_ids:
            total_qty += line.total_qty_material
        return total_qty

    def sum_total_qty_finished(self, plan):
        total_qty = 0
        for line in plan.section_ids:
            total_qty += line.qty
        return total_qty


