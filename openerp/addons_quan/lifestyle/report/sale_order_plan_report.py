from openerp.report import report_sxw
from operator import itemgetter


class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_sections': self.get_sections,  #
            'get_list_material': self.get_list_material,  #
            'get_list_finished': self.get_list_finished,  #
            'get_list_sections': self.get_list_sections,  #
            'conversion_currency': self.conversion_currency,  #
            'get_detail_sections': self.get_detail_sections,  #
            'get_order_line': self.get_order_line,  #
            'get_purchase_order': self.get_purchase_order,
            'get_purchase_order_line': self.get_purchase_order_line,
            'get_info_sections': self.get_info_sections,
            '_get_total': self._get_total,

            '_get_all_total': self._get_all_total,  #
            '_get_list_material': self._get_list_material,
            '_get_total_amount_material': self._get_total_amount_material,  #
            '_get_total_amount_fproduct': self._get_total_amount_fproduct,  #
            '_get_other_expense': self._get_other_expense,  #
        })
        self.context = context

    def get_order_line(self, order_lines):
        print 'production Plan'
        return [{'name': line.name or '', 'id': line.id} for line in order_lines]

    def get_sections(self, order_lines_id):
        plan_obj = self.pool.get('production.plan')
        result = []
        stt = 1
        plan_ids = plan_obj.search(self.cr, self.uid, [('sale_line_id', '=', order_lines_id)])
        for plan in plan_obj.browse(self.cr, self.uid, plan_ids):
            for i, section in enumerate(plan.section_ids):
                result.append({
                    'id': section.id,
                    'stt': i + 1,
                    'name': section.name or '',
                    'stock': section.stock_plan_id and section.stock_plan_id.name or '',
                    'product': section.product_id and section.product_id.name or '',
                    'quantity': section.qty or 0,
                    'uom': section.product_id.uom_id.name or '',
                    'kg': section.qty_kg or 0,
                })
        return result

    def get_detail_sections(self, line):
        plan_obj = self.pool.get('production.plan')
        result = []
        stt = 1
        plan_ids = plan_obj.search(self.cr, self.uid, [('sale_line_id', '=', line.id)])
        if plan_ids:
            for plan in plan_obj.browse(self.cr, self.uid, plan_ids):
                for section in plan.section_ids:
                    # name += ', %s' % move.stock_id.name
                    name = section.name or ''
                    name += ' - [ %s ]' % section and section.stock_plan_id and section.stock_plan_id.name
                    total_price = sum([material.quantity * material.price_unit for material in section.material_ids])
                    res = {
                        'id': section.id,
                        'stt': stt,
                        'name': name,
                        'total_qty': section.total_qty_material or 0,
                        'total_price': total_price or '',
                    }
                    stt += 1
                    result.append(res)
        return result

    def get_list_material(self, section_id):
        section_obj = self.pool.get('production.section')
        result = []
        for section in section_obj.browse(self.cr, self.uid, [section_id]):
            ids_old = []
            for line in sorted(section.material_ids):
                if line.product_id.id not in ids_old:
                    res = {
                        'id': line.product_id.id,
                        'name': line.product_id and line.product_id.name or False,
                        'total': self.total_qty_material(section.material_ids, line.product_id.id),
                        'detail': self.detail_material(section, line.product_id.id),
                    }
                    ids_old.append(line.product_id.id)
                    result.append(res)
        return result


    def get_list_finished(self, section_id):
        section_obj = self.pool.get('production.section')
        result = []
        for section in section_obj.browse(self.cr, self.uid, [section_id]):
            res = {
                'name': section.product_id and section.product_id.name or False,
                'total': self.total_qty_finished(section.finished_ids),
                'price': section.price,
                'total_price': self.total_price_finished(section.finished_ids),
                'detail': self.detail_finished(section),
            }
            result.append(res)
        return result

    # get_list_sections
    def get_list_sections(self, o):
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_config_obj = self.pool.get('init.section')
        result = []
        lst_section_config = section_config_obj.search(cr, uid, [])
        for section_config in section_config_obj.browse(cr, uid, lst_section_config):
            lst_section = section_obj.search(cr, uid,
                                             [('section_config_id', '=', section_config.id), ('sale_id', '=', o.id)])
            if lst_section:
                res = {
                    'total': sum(
                        [(section.price * section.qty) for section in section_obj.browse(cr, uid, lst_section)]),
                    'name': section_config.name or ''
                }
                result.append(res)
        return result


    def get_purchase_order(self, o):
        result = []
        list_po = []
        purchase_obj = self.pool.get('purchase.order')
        purchase_line_obj = self.pool.get('purchase.order.line')
        list_pol = purchase_line_obj.search(self.cr, self.uid, [('sale_line_id.order_id', '=', o.id)])
        for pol in purchase_line_obj.browse(self.cr, self.uid, list_pol):
            list_po.append(pol.order_id.id)
        list_po = list(set(list_po))
        if list_po:
            for po in purchase_obj.browse(self.cr, self.uid, list_po):
                res = {
                    'name': po.name or '',
                    'id': po.id or False,
                }
                result.append(res)
        return result

    def get_purchase_order_line(self, po_id):
        result = []
        purchase_line_obj = self.pool.get('purchase.order.line')
        list_po_line = purchase_line_obj.search(self.cr, self.uid,
                                                [('order_id', '=', po_id), ('state', 'not in', ('draft', 'cancel'))])
        if list_po_line:
            for line in purchase_line_obj.browse(self.cr, self.uid, list_po_line):
                res = {
                    'name': line.name or '',
                    'qty': line.product_qty or 0,
                    'uom': line.product_uom.name or 0,
                    'total': line.price_subtotal or 0,
                }
                result.append(res)
        return result

    def get_info_sections(self, line):
        plan_obj = self.pool.get('production.plan')
        section_obj = self.pool.get('production.section')
        result = []
        temp = []
        stt = 1
        plan_ids = plan_obj.search(self.cr, self.uid, [('sale_line_id', '=', line.id)])
        if plan_ids:
            for plan in plan_obj.browse(self.cr, self.uid, plan_ids):
                for section in plan.section_ids:
                    if section.section_config_id.id not in temp:
                        temp.append(section.section_config_id.id)
                for temp_id in temp:
                    section_ids = section_obj.search(self.cr, self.uid,
                                                     [('plan_id', '=', plan.id), ('section_config_id', '=', temp_id)])
                    if section_ids:
                        qty = 0
                        total = 0
                        for section in section_obj.browse(self.cr, self.uid, section_ids):
                            qty += section.qty
                            total += section.qty * section.price
                        res = {
                            'qty': qty,
                            'total': total,
                            'stt': stt,
                            'name': section.section_config_id.name or '',
                        }
                        stt += 1
                        result.append(res)
        return result

    def total_qty_material(self, material_ids, product_id):
        return sum([m.quantity for m in material_ids if m.product_id.id == product_id])

    def detail_material(self, section, product_id):
        result = []
        for line in section.material_ids:
            if line.product_id.id == product_id:
                res = {
                    'quantity': line.quantity or 0,
                    'price_unit': line.price_unit or '',
                    'total': line.quantity * line.price_unit or '',
                    'partner': line.partner_id and line.partner_id.name or '',
                    'date_in': line.date_in,
                    'stock': section.stock_plan_id and section.stock_plan_id.name or False,
                    'stock_from': line.stock_plan_id and line.stock_plan_id.name or False,
                }
                result.append(res)
        return result

    def detail_finished(self, section):
        result = []
        for line in section.finished_ids:
            res = {
                'quantity': line.quantity or 0,
                'date_out': line.date_out,
                'stock': section.stock_plan_id and section.stock_plan_id.name or False,
                'date_finished': line.date_finished or False,
            }
            result.append(res)
        return result

    def total_price_finished(self, finished_ids):
        return sum([f.quantity * f.section_finished_id.price for f in finished_ids])

    def total_qty_finished(self, finished_ids):
        return sum([f.quantity for f in finished_ids])

    def conversion_currency(self, order, company):
        currency_obj = self.pool.get('res.currency')
        rate = currency_obj._get_conversion_rate(self.cr, self.uid, order.pricelist_id.currency_id, company.currency_id)
        return order.amount_total * rate

    def _get_total(self, order_lines_id):
        plan_obj = self.pool.get('production.plan')
        plan_ids = plan_obj.search(self.cr, self.uid, [('sale_line_id', '=', order_lines_id)])
        res = {}
        if plan_ids:
            for plan in plan_obj.browse(self.cr, self.uid, plan_ids):
                qty = 0
                price = 0
                for section in plan.section_ids:
                    qty += section.qty
                    price += section.price * section.qty
            res = {
                'qty': qty or 0,
                'price': price or 0,
            }
        return res

    def _get_other_expense(self, so):
        total = 0
        cr = self.cr
        uid = self.uid
        other_cost_obj = self.pool.get('other.cost')
        list_cost = other_cost_obj.search(cr, uid, [('sale_id', '=', so.id)])
        total = sum([(cost.price_subtotal) for cost in other_cost_obj.browse(cr, uid, list_cost)])
        return total

    def _get_total_amount_material(self, so):
        total = 0
        cr = self.cr
        uid = self.uid
        section_obj = self.pool.get('production.section')
        section_lst = section_obj.search(cr, uid, [('sale_id', '=', so.id)])
        for section in section_obj.browse(cr, uid, section_lst):
            for material in section.material_ids:
                total += material.quantity * material.price_unit
        return total

    def _get_total_amount_fproduct(self, so):
        total = 0
        cr = self.cr
        uid = self.uid
        list_section = []
        section_obj = self.pool.get('production.section')
        cr.execute("""SELECT ps.id
                        FROM production_section ps
                            INNER JOIN production_plan pl on (ps.plan_id = pl.id) 
                            INNER JOIN sale_order_line sol on (pl.sale_line_id = sol.id) 
                            INNER JOIN sale_order so on (sol.order_id = so.id) 
                            INNER JOIN production_material pm on (pm.section_material_id = ps.id) 
                        WHERE 
                            so.id = %s 
                            """ % (so.id))
        seq = map(itemgetter(0), cr.fetchall())
        list_section = list(set(seq))
        total = sum([(sec.price * sec.qty) for sec in section_obj.browse(cr, uid, list_section)])
        return total

    def _get_all_total(self, so, company):
        total = 0
        total += self._get_total_amount_material(so)
        total += self._get_total_amount_fproduct(so)
        total += self._get_other_expense(so)
        return total

    def _get_list_material(self, so):
        cr = self.cr
        uid = self.uid
        pol_obj = self.pool.get('purchase.order.line')
        res = []
        result = []
        list_pro = []
        list_pol = pol_obj.search(self.cr, self.uid, [('sale_line_id.order_id', '=', so.id)])
        for pol in pol_obj.browse(cr, uid, list_pol):
            list_pro.append(pol.product_id.id)
            res = {
                'name': pol.product_id.name or '',
                'id': pol.product_id.id or False,
            }
            if res not in result: result.append(res)
        return result       
    
    
        
