# -*- coding: utf-8 -*-
import re

from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.hide_cost_price_margin.models.hide_cost import GROUP_XMLID, STRICT_PARAM, mark_arch

COST_MODELS = {
    'product.template': ['standard_price'],
    'product.product': ['standard_price'],
    'sale.order': ['margin', 'margin_percent'],
    'sale.order.line': ['purchase_price', 'margin', 'margin_percent'],
}


@tagged('post_install', '-at_install')
class TestHideCostPriceMargin(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True, no_reset_password=True))
        Users = cls.env['res.users']
        cls.groups_field = 'group_ids' if 'group_ids' in Users._fields else 'groups_id'
        cls.cost_group = cls.env.ref(GROUP_XMLID)
        export_group = cls.env.ref('base.group_allow_export', raise_if_not_found=False)
        extra = export_group.ids if export_group else []

        def make_user(login, xmlids):
            group_ids = [cls.env.ref(x).id for x in xmlids] + extra
            return Users.create({
                'name': login.title(), 'login': login, 'email': '%s@example.com' % login,
                cls.groups_field: [(6, 0, group_ids)],
            })

        cls.salesman = make_user('hcp_salesman', ['base.group_user', 'sales_team.group_sale_salesman'])
        cls.sale_manager = make_user('hcp_sale_manager', ['base.group_user', 'sales_team.group_sale_manager'])
        cls.stock_user = make_user('hcp_stock_user', ['base.group_user', 'stock.group_stock_user'])
        cls.stock_manager = make_user('hcp_stock_manager', ['base.group_user', 'stock.group_stock_manager'])

        product_vals = {'name': 'HCP Widget', 'list_price': 100.0, 'standard_price': 60.0}
        Template = cls.env['product.template']
        if 'is_storable' in Template._fields:          # 18.0+
            product_vals.update(type='consu', is_storable=True)
        elif 'detailed_type' in Template._fields:      # 16.0
            product_vals.update(detailed_type='product')
        else:                                          # 17.0
            product_vals.update(type='product')
        cls.template = Template.create(product_vals)
        cls.product = cls.template.product_variant_id
        cls.partner = cls.env['res.partner'].create({'name': 'HCP Customer'})

    # ------------------------------------------------------------------ helpers
    def _set_strict(self, value):
        Param = self.env['ir.config_parameter'].sudo()
        if hasattr(Param, 'set_bool'):  # 20.0+
            Param.set_bool(STRICT_PARAM, value)
        else:
            Param.set_param(STRICT_PARAM, 'True' if value else 'False')

    def _arch(self, user, model, view_type, view_id=None):
        return self.env[model].with_user(user).get_view(view_id, view_type)['arch']

    @staticmethod
    def _shows(arch, field):
        """True if the arch still has a node (field or label) or a template reference for ``field``."""
        pattern = r'(name|for)="%s"|record\.%s\b' % (field, field)
        return bool(re.search(pattern, arch))

    def _create_order(self, user, pricelist=None):
        vals = {
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 2.0, 'price_unit': 100.0})],
        }
        if pricelist:
            vals['pricelist_id'] = pricelist.id
            vals['order_line'] = [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 2.0})]
        return self.env['sale.order'].with_user(user).create(vals)

    def _read_group(self, records, fields, groupby):
        """Public grouped read through the API of the running series."""
        if hasattr(records, 'formatted_read_group'):
            return records.formatted_read_group([], groupby, fields)
        return records.read_group([], fields, groupby)

    # ------------------------------------------------------------------ groups
    def test_01_group_implied_for_admins_and_managers(self):
        self.assertTrue(self.env.ref('base.user_admin').has_group(GROUP_XMLID))
        self.assertTrue(self.sale_manager.has_group(GROUP_XMLID))
        self.assertTrue(self.stock_manager.has_group(GROUP_XMLID))
        self.assertFalse(self.salesman.has_group(GROUP_XMLID))
        self.assertFalse(self.stock_user.has_group(GROUP_XMLID))

    # ------------------------------------------------------------------ views
    def test_02_product_views_hide_cost_for_salesman(self):
        for model in ('product.template', 'product.product'):
            for view_type in ('form', 'list' if self._has_list() else 'tree', 'kanban'):
                arch = self._arch(self.salesman, model, view_type)
                self.assertFalse(self._shows(arch, 'standard_price'), '%s %s view shows cost' % (model, view_type))
        # the "per unit" wrapper of the cost goes with it (series that have it)
        for model in ('product.template', 'product.product'):
            if 'standard_price_uom' in self._arch(self.sale_manager, model, 'form'):
                self.assertNotIn('standard_price_uom', self._arch(self.salesman, model, 'form'))
        # managers still see the cost on the product form and list
        for user in (self.sale_manager, self.stock_manager):
            self.assertTrue(self._shows(self._arch(user, 'product.template', 'form'), 'standard_price'))
            self.assertTrue(self._shows(
                self._arch(user, 'product.template', 'list' if self._has_list() else 'tree'), 'standard_price'))

    def test_03_sale_order_form_hides_margin_and_line_cost(self):
        arch = self._arch(self.salesman, 'sale.order', 'form')
        for field in ('margin', 'margin_percent', 'purchase_price'):
            self.assertFalse(self._shows(arch, field), 'salesman sees %s on the order form' % field)
        manager_arch = self._arch(self.sale_manager, 'sale.order', 'form')
        for field in ('margin', 'margin_percent', 'purchase_price'):
            self.assertTrue(self._shows(manager_arch, field), 'manager lost %s on the order form' % field)

    def test_04_every_primary_view_is_clean_for_salesman(self):
        View = self.env['ir.ui.view']
        view_types = ['form', 'kanban', 'search', 'pivot', 'graph', 'list' if self._has_list() else 'tree']
        checked = 0
        for model, fields in COST_MODELS.items():
            views = View.search([('model', '=', model), ('mode', '=', 'primary'), ('type', 'in', view_types)])
            for view in views:
                arch = self._arch(self.salesman, model, view.type, view.id)
                for field in fields:
                    self.assertFalse(self._shows(arch, field),
                                     'view %s (%s) still shows %s' % (view.xml_id or view.name, model, field))
                checked += 1
        self.assertGreater(checked, 10)

    def test_05_wrappers_and_labels_are_hidden_with_the_field(self):
        arch = etree.fromstring(
            '<form><group>'
            '<label for="standard_price"/>'
            '<div name="standard_price_uom"><field name="standard_price"/><span>per <field name="uom_id"/></span></div>'
            '<div class="o_row"><field name="standard_price"/></div>'
            '<field name="list_price"/>'
            '<field name="standard_price" groups="base.group_no_one"/>'
            '</group></form>')
        self.assertEqual(mark_arch(self.env, arch, 'product.template'), 4)
        group = arch[0]
        self.assertEqual(group[0].get('groups'), GROUP_XMLID)                    # label
        self.assertEqual(group[1].get('groups'), GROUP_XMLID)                    # named wrapper div
        self.assertEqual(group[2].get('groups'), GROUP_XMLID)                    # div holding only the cost
        self.assertIsNone(group[3].get('groups'))                                # list price untouched
        self.assertEqual(group[4].tag, 't')                                      # existing groups kept
        self.assertEqual(group[4].get('groups'), GROUP_XMLID)
        self.assertEqual(group[4][0].get('groups'), 'base.group_no_one')

    def test_06_margin_block_and_x2many_subviews(self):
        arch = etree.fromstring(
            '<form><group>'
            '<div class="d-flex"><label for="margin"/><div><field name="margin"/>'
            '<field name="amount_untaxed" invisible="1"/>'
            '<span>(<field name="margin_percent"/>)</span></div></div>'
            '<field name="amount_total"/>'
            '<field name="order_line"><list><field name="price_unit"/><field name="purchase_price"/>'
            '<field name="margin"/></list></field>'
            '</group></form>')
        mark_arch(self.env, arch, 'sale.order')
        self.assertEqual(arch[0][0].get('groups'), GROUP_XMLID)           # whole margin block
        self.assertIsNone(arch[0][1].get('groups'))                       # amount_total untouched
        line_list = arch[0][2][0]
        self.assertIsNone(line_list[0].get('groups'))                     # price_unit untouched
        self.assertEqual(line_list[1].get('groups'), GROUP_XMLID)         # line cost
        self.assertEqual(line_list[2].get('groups'), GROUP_XMLID)         # line margin

    # ------------------------------------------------------------------ fields_get / get_views
    def test_07_fields_get_hides_cost_for_salesman_only(self):
        for model, fields in COST_MODELS.items():
            salesman_fields = self.env[model].with_user(self.salesman).fields_get()
            manager_fields = self.env[model].with_user(self.sale_manager).fields_get()
            for field in fields:
                self.assertNotIn(field, salesman_fields, '%s.%s visible in fields_get' % (model, field))
                self.assertIn(field, manager_fields)
        self.assertIn('list_price', self.env['product.template'].with_user(self.salesman).fields_get())

    def test_08_get_views_drops_margin_measure_for_salesman(self):
        list_type = 'list' if self._has_list() else 'tree'
        views = [[False, list_type], [False, 'form'], [False, 'pivot'], [False, 'search']]
        res = self.env['sale.order'].with_user(self.salesman).get_views(views)
        fields = self._model_fields(res, 'sale.order')
        self.assertNotIn('margin', fields)
        self.assertIn('amount_total', fields)
        res = self.env['sale.order'].with_user(self.sale_manager).get_views(views)
        self.assertIn('margin', self._model_fields(res, 'sale.order'))

    # ------------------------------------------------------------------ export
    def test_09_export_of_cost_blocked_for_salesman(self):
        with self.assertRaises(AccessError):
            self.template.with_user(self.salesman).export_data(['name', 'standard_price'])
        order = self._create_order(self.salesman)
        with self.assertRaises(AccessError):
            order.with_user(self.salesman).export_data(['name', 'order_line/margin'])
        with self.assertRaises(AccessError):
            order.order_line.with_user(self.salesman).export_data(['product_id/standard_price'])
        with self.assertRaises(AccessError):
            order.with_user(self.salesman).export_data(['margin'])

    def test_10_export_of_other_fields_still_works(self):
        rows = self.template.with_user(self.salesman).export_data(['name', 'list_price', 'categ_id/id'])['datas']
        self.assertEqual(rows[0][0], 'HCP Widget')
        rows = self.template.with_user(self.sale_manager).export_data(['name', 'standard_price'])['datas']
        self.assertEqual(float(rows[0][1]), 60.0)
        rows = self.template.with_user(self.salesman).sudo().export_data(['standard_price'])['datas']
        self.assertEqual(float(rows[0][0]), 60.0)

    # ------------------------------------------------------------------ business flows
    def test_11_salesman_creates_and_confirms_order_margin_computed(self):
        order = self._create_order(self.salesman)
        order.with_user(self.salesman).action_confirm()
        self.assertIn(order.state, ('sale', 'done'))
        line = order.order_line.sudo()
        self.assertAlmostEqual(line.purchase_price, 60.0)
        self.assertAlmostEqual(line.margin, 80.0)
        self.assertAlmostEqual(order.sudo().margin, 80.0)

    def test_12_default_mode_keeps_python_reads_working(self):
        # default mode only hides: other modules reading the cost as the user keep working
        self.assertEqual(self.product.with_user(self.salesman).standard_price, 60.0)
        values = self.template.with_user(self.salesman).read(['standard_price'])[0]
        self.assertEqual(values['standard_price'], 60.0)

    def test_13_strict_mode_blocks_api_reads_and_writes(self):
        self._set_strict(True)
        product = self.template.with_user(self.salesman)
        product.invalidate_recordset()
        with self.assertRaises(AccessError):
            product.read(['standard_price'])
        order = self._create_order(self.salesman)
        with self.assertRaises(AccessError):
            self.env['sale.order'].with_user(self.salesman).search_read([('id', '=', order.id)], ['margin'])
        with self.assertRaises(AccessError):
            order.order_line.with_user(self.salesman).write({'purchase_price': 1.0})
        # managers are not affected
        self.assertEqual(self.template.with_user(self.sale_manager).read(['standard_price'])[0]['standard_price'], 60.0)
        # back to default mode: reads work again
        self._set_strict(False)
        self.template.invalidate_recordset()
        self.assertEqual(self.template.with_user(self.salesman).read(['standard_price'])[0]['standard_price'], 60.0)

    def test_14_strict_mode_blocks_grouped_margin(self):
        self._create_order(self.salesman)
        self._set_strict(True)
        with self.assertRaises(AccessError):
            self._read_group(self.env['sale.order'].with_user(self.salesman), ['margin:sum'], ['partner_id'])
        res = self._read_group(self.env['sale.order'].with_user(self.sale_manager), ['margin:sum'], ['partner_id'])
        self.assertTrue(res)

    def test_15_strict_mode_order_flow_and_cost_pricelist(self):
        self._set_strict(True)
        order = self._create_order(self.salesman)
        order.with_user(self.salesman).action_confirm()
        self.assertAlmostEqual(order.order_line.sudo().margin, 80.0)
        # a pricelist "cost + 25%" still prices the line for a salesman who cannot read the cost
        Item = self.env['product.pricelist.item']
        item_vals = {'applied_on': '3_global', 'base': 'standard_price', 'price_discount': -25.0}
        if 'markup' in dict(Item._fields['compute_price'].selection):   # 20.0+
            item_vals.update(compute_price='markup', price_markup=25.0)
        else:
            item_vals.update(compute_price='formula')
        pricelist = self.env['product.pricelist'].create({'name': 'Cost plus 25', 'item_ids': [(0, 0, item_vals)]})
        order = self._create_order(self.salesman, pricelist=pricelist)
        self.assertAlmostEqual(order.order_line.sudo().price_unit, 75.0)

    def test_16_stock_user_validates_receipt_in_both_modes(self):
        avco_category = self.env['product.category'].create({'name': 'HCP AVCO'})
        avco_category.property_cost_method = 'average'
        avco_product = self.template.copy({'name': 'HCP AVCO Widget', 'categ_id': avco_category.id}).product_variant_id
        avco_product.standard_price = 10.0
        runs = [(False, self.product), (True, self.product), (False, avco_product), (True, avco_product)]
        for strict, product in runs:
            self._set_strict(strict)
            picking_type = self.env.ref('stock.picking_type_in')
            supplier = self.env.ref('stock.stock_location_suppliers')
            stock_location = picking_type.default_location_dest_id or self.env.ref('stock.stock_location_stock')
            Picking = self.env['stock.picking'].with_user(self.stock_user)
            move_vals = {'product_id': product.id, 'product_uom_qty': 5.0, 'price_unit': 20.0,
                         'location_id': supplier.id, 'location_dest_id': stock_location.id}
            Move = self.env['stock.move']
            if 'name' in Move._fields and Move._fields['name'].required:
                move_vals['name'] = product.display_name
            if 'product_uom' in Move._fields:
                move_vals['product_uom'] = product.uom_id.id
            picking = Picking.create({
                'picking_type_id': picking_type.id,
                'location_id': supplier.id,
                'location_dest_id': stock_location.id,
                'move_ids': [(0, 0, move_vals)],
            })
            picking.action_confirm()
            move = picking.move_ids
            if 'quantity_done' in move._fields:
                move.quantity_done = 5.0
            else:
                move.quantity = 5.0
                if 'picked' in move._fields:
                    move.picked = True
            picking.button_validate()
            self.assertEqual(picking.state, 'done', 'receipt not validated (strict=%s)' % strict)
        self.assertEqual(self.product.sudo().qty_available, 10.0)
        self.assertEqual(avco_product.sudo().qty_available, 10.0)
        # the average-cost product went through the AVCO valuation code as the stock user
        self.assertEqual(avco_product.categ_id.property_cost_method, 'average')
        self.assertGreater(avco_product.sudo().standard_price, 0.0)

    def test_17_granting_the_group_reveals_cost(self):
        self.salesman.write({self.groups_field: [(4, self.cost_group.id)]})
        self.assertTrue(self.salesman.has_group(GROUP_XMLID))
        self.assertTrue(self._shows(self._arch(self.salesman, 'product.template', 'form'), 'standard_price'))
        self.assertIn('standard_price', self.env['product.template'].with_user(self.salesman).fields_get())
        rows = self.template.with_user(self.salesman).export_data(['standard_price'])['datas']
        self.assertEqual(float(rows[0][0]), 60.0)

    def test_18_settings_toggle_strict_mode(self):
        self.assertFalse(self.env['product.template']._hcp_is_strict())
        settings = self.env['res.config.settings'].create({'hcp_strict_mode': True})
        settings.execute()
        self.assertTrue(self.env['product.template']._hcp_is_strict())
        settings = self.env['res.config.settings'].create({'hcp_strict_mode': False})
        settings.execute()
        self.assertFalse(self.env['product.template']._hcp_is_strict())

    def test_19_inventory_valuation_fields_hidden_for_stock_user(self):
        from odoo.addons.hide_cost_price_margin.models.hide_cost import hidden_names
        View = self.env['ir.ui.view']
        view_types = ['form', 'kanban', 'pivot', 'graph', 'list' if self._has_list() else 'tree']
        checked = 0
        for model in ('product.product', 'stock.lot', 'stock.move'):
            fields = hidden_names(self.env, model)
            if not fields:
                continue
            for view in View.search([('model', '=', model), ('mode', '=', 'primary'), ('type', 'in', view_types)]):
                arch = self._arch(self.stock_user, model, view.type, view.id)
                for field in fields:
                    self.assertFalse(re.search(r'<field [^>]*name="%s"' % field, arch),
                                     'view %s (%s) still shows %s' % (view.xml_id or view.name, model, field))
                checked += 1
            manager_fields = self.env[model].with_user(self.stock_manager).fields_get()
            user_fields = self.env[model].with_user(self.stock_user).fields_get()
            for field in fields:
                self.assertIn(field, manager_fields)
                self.assertNotIn(field, user_fields)
        self.assertGreater(checked, 3)

    # ------------------------------------------------------------------ utils
    def _has_list(self):
        return 'list' in dict(self.env['ir.ui.view']._fields['type'].selection)

    @staticmethod
    def _model_fields(res, model):
        info = res['models'][model]
        return info['fields'] if isinstance(info.get('fields'), dict) else info
