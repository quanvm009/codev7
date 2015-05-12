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
#2
######################################################################

{
    'name': 'Life Style',
    'version': '7.0.1',
    'category': 'INIT',
    'sequence': 11,
    'summary': '',
    'description': '',
    'author': 'lapdx@init.vn',
    'website': 'www.init.vn',
    'images': [],
    'depends': ['base', 'stock','sale', 'purchase', 'product',  'sale_stock', 'stock_cancel', 'report_aeroo'],
    'data': [
        'security/life_style_security.xml',
        #             'security/ir.model.access.csv',
        'data/user/ir.model.access.csv',
        'data/viewer/ir.model.access.csv',

        'wizard/split_move_wizard_view.xml',

        'view/production_section_view.xml',
        'view/stock_move.xml',
        'view/product_color_view.xml',
        'view/product_product_view.xml',
        'view/sale_order_view.xml',

        'view/production_plan_view.xml',
        'view/res_partner_view.xml',
        'view/partner_sequence.xml',
        'view/partner_sequence_2.xml',

        'view/plan_sequence.xml',
        'view/plan_sale_sequence.xml',
        'view/production_plan_report_view.xml',
        'view/invoice_report_view.xml',
        'view/schedule_for_production_report.xml',
        'view/product_uom_view.xml',
        'view/account_invoice_view.xml',
        'view/purchase_view.xml',
        'view/pl_report_define.xml',
        'view/order_tracking_view.xml',
        'view/order_report_view.xml',
        'view/production_plan_sale_view.xml',
        'view/res_users_view.xml',
        'view/other_cost_view.xml',
        'view/internal_order_view.xml',
        'view/stock_view.xml',

        # define wizard view

        'wizard/create_po_wizard_view.xml',
        'wizard/create_out_material_pre_wizard_view.xml',
        'wizard/create_out_material_wizard_view.xml',
        'wizard/create_in_finished_wizard_view.xml',
        'wizard/wizard_pl_report_view.xml',
        'wizard/wizard_order_report_view.xml',
        'wizard/wizard_print_order_tracking_view.xml',
        'wizard/section_wizard_report_view.xml',
        'wizard/create_out_finished_wizard_view.xml',
        'wizard/invoice_factory_wizard_view.xml',
        'wizard/init_create_warehouse_wizard.xml',
        'wizard/stock_partial_picking_view.xml',
        'wizard/edit_sale_order_wizard_view.xml',


        # define report view

        'report/report_define.xml',
        'report/sale_report_view.xml',
        'report/plan_report_view.xml',
        'report/sale_order_plan_report_view.xml',
        'report/report_stock_move_view.xml',

    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
