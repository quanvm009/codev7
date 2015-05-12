from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
import random
from openerp.osv import fields, osv
import time
from openerp import pooler


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'get_contact': self.get_contact,
            'get_total_qty': self.get_total_qty,
        })
        self.context = context

    def get_contact(self, contacts):
        name = ''
        if contacts:
            name = contacts[0].name
            if contacts[0].phone:
                name += '(%s)' % contacts[0].phone
        return name

    def get_total_qty(self, lines):
        total1 = 0
        total2 = 0
        for line in lines:
            total1 += line.qty
            total2 += line.product_qty
        return [total1, total2]
    
