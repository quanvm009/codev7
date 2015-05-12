# -*- coding: utf-8 -*-
##############################################################################
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
import os
import os.path
import shutil

from openerp.osv import fields, osv

class init_i18n(osv.osv):
    _name = "init.i18n"
    _columns = {
        'name': fields.text('Log'),
    }
    
    def remove_file_if_exist(self, filename):
        try:
            os.remove(filename)
        except:
            pass
        return True
    
    def load_language(self, cr, uid, ids, context={}):
        lang = 'vi_VN'
        context = {'overwrite': True}
        modobj = self.pool.get('ir.module.module')
        mids = modobj.search(cr, uid, [('state', '=', 'installed')])
        modobj.update_translations(cr, uid, mids, lang, context or {})
        return True
        
    def copy_translated_file_to_addons_i18n(self, cr, uid, ids, context={}):
        # get current directory
        current_path = os.path.dirname(__file__)
        openerp_path = os.path.dirname(current_path)
        i18n_path = os.path.join(current_path, 'i18n')
        list_files = os.listdir(i18n_path)
        str = "Begining copy ...\n"
        for lf in list_files:
            addon_name = os.path.splitext(lf)[0]
            cp_from = os.path.join(i18n_path, lf)
            other_addon_path = os.path.join(openerp_path, addon_name)
            cp_to = os.path.join(other_addon_path, os.path.join('i18n', 'vi.po'))
            str += "Copy from: %s to %s" %(cp_from, cp_to)
            try:
                self.remove_file_if_exist(cp_to)
                shutil.copy2(cp_from, cp_to)
            except:
                str += "\nError when copying..."
        str += "\nEnding copy..."
        # load language
#        self.load_language(cr, uid, ids, context)
        self.write(cr, uid, ids, {'name': str})  
        return True
    
init_i18n()