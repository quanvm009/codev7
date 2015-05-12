# -*- coding: utf-8 -*- 
# #####################################################################
# 
# OpenERP, Open Source Management Solution 
# Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>). 
# Copyright (C) 2013 INIT Tech Co., Ltd (http://init.vn). 
# This program is free software: you can redistribute it and/or modify 
# it under the terms of the GNU Affero General Public License as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version. 
# 
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
# GNU Affero General Public License for more details. 
# 
# You should have received a copy of the GNU Affero General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>. 
# 
######################################################################

import time
import openerp.addons.decimal_precision as dp
from openerp.addons.lifestyle.model.datetime_utils import *

from dateutil.relativedelta import relativedelta
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.float_utils import float_is_zero
from openerp.tools.translate import _
from openerp import netsvc
from operator import itemgetter


class edit_sale_order_wizard(osv.osv_memory):
    _name = "edit.sale.order.wizard"

    def default_get(self, cr, uid, fields, context):
        if context is None:
            context = {}
        res = super(edit_sale_order_wizard, self).default_get(cr, uid, fields, context=context)
        obj_sale = self.pool.get('sale.order').browse(cr, uid, context['active_ids'])[0]
        lst_id = [line.id for line in obj_sale.order_line]
        res['order_line'] = lst_id
        return res

    _columns = {
        'order_line': fields.one2many('sale.order.line', 'order_id', 'Order Lines'),
    }
    _defaults = {
    }

    def button_validate(self, cr, uid, ids, context=None):
        return {}

    def button_cancel(self, cr, uid, ids, context=None):
        return {}


edit_sale_order_wizard()








