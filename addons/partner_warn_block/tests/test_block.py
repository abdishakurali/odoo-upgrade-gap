from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBlock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "Slow Payer Ltd", "sale_warn_msg": "Pays 90 days late.", "sale_block": True})
        cls.contact = cls.env["res.partner"].create({"name": "Buyer", "parent_id": cls.customer.id})
        cls.fine = cls.env["res.partner"].create({"name": "Good Customer"})
        cls.product = cls.env["product.product"].create({"name": "Widget", "list_price": 10.0})

    def sale(self, partner, **kw):
        return self.env["sale.order"].create({"partner_id": partner.id, **kw})

    # -- sales ------------------------------------------------------------------------------
    def test_a_blocked_customer_cannot_get_a_sales_order(self):
        with self.assertRaises(ValidationError) as caught:
            self.sale(self.customer)
        self.assertIn("Pays 90 days late.", str(caught.exception))
        self.assertIn("Slow Payer Ltd", str(caught.exception))

    def test_a_contact_of_a_blocked_company_is_blocked_too(self):
        with self.assertRaises(ValidationError):
            self.sale(self.contact)

    def test_an_unblocked_customer_is_not_affected(self):
        order = self.sale(self.fine, order_line=[(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})])
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_blocking_after_the_quotation_exists_stops_the_confirmation(self):
        order = self.sale(self.fine, order_line=[(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})])
        self.fine.write({"sale_block": True, "sale_warn_msg": "On hold."})
        with self.assertRaises(ValidationError):
            order.action_confirm()
        self.assertEqual(order.state, "draft")

    def test_a_warning_without_block_does_not_stop_anything(self):
        partner = self.env["res.partner"].create({"name": "Just a note", "sale_warn_msg": "Prefers email."})
        self.assertTrue(self.sale(partner))

    def test_choosing_a_blocked_customer_in_the_form_shows_the_reason_and_clears_it(self):
        order = self.env["sale.order"].new({"partner_id": self.customer.id})
        result = order._onchange_partner_block()
        self.assertIn("Pays 90 days late.", result["warning"]["message"])
        self.assertFalse(order.partner_id)

    def test_no_reason_given_still_blocks_with_a_clear_text(self):
        partner = self.env["res.partner"].create({"name": "No reason", "sale_block": True})
        with self.assertRaises(ValidationError) as caught:
            self.sale(partner)
        self.assertIn("No reason given.", str(caught.exception))

    # -- products ---------------------------------------------------------------------------
    def test_a_blocked_product_cannot_be_sold(self):
        self.product.product_tmpl_id.write({"sale_line_block": True, "sale_line_warn_msg": "Recalled batch."})
        with self.assertRaises(ValidationError) as caught:
            self.sale(self.fine, order_line=[(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})])
        self.assertIn("Recalled batch.", str(caught.exception))

    def test_a_product_warning_without_block_is_allowed(self):
        self.product.product_tmpl_id.sale_line_warn_msg = "Check the colour."
        self.assertTrue(self.sale(self.fine, order_line=[(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})]))

    # -- purchases --------------------------------------------------------------------------
    def test_a_blocked_vendor_cannot_get_a_purchase_order(self):
        vendor = self.env["res.partner"].create({"name": "Bad Vendor", "purchase_block": True, "purchase_warn_msg": "Quality problems."})
        with self.assertRaises(ValidationError) as caught:
            self.env["purchase.order"].create({"partner_id": vendor.id})
        self.assertIn("Quality problems.", str(caught.exception))

    def test_a_blocked_product_cannot_be_purchased(self):
        self.product.product_tmpl_id.write({"purchase_line_block": True, "purchase_line_warn_msg": "Discontinued."})
        vendor = self.env["res.partner"].create({"name": "Vendor"})
        with self.assertRaises(ValidationError):
            self.env["purchase.order"].create({"partner_id": vendor.id, "order_line": [(0, 0, {"product_id": self.product.id, "product_qty": 1, "price_unit": 5})]})

    # -- invoices ---------------------------------------------------------------------------
    def test_a_blocked_contact_cannot_be_invoiced(self):
        partner = self.env["res.partner"].create({"name": "No invoices", "invoice_block": True, "invoice_warn_msg": "Credit check first."})
        with self.assertRaises(ValidationError) as caught:
            self.env["account.move"].create({"move_type": "out_invoice", "partner_id": partner.id})
        self.assertIn("Credit check first.", str(caught.exception))

    def test_the_invoice_message_is_shown_on_the_draft_invoice(self):
        partner = self.env["res.partner"].create({"name": "Notice", "invoice_warn": "warning", "invoice_warn_msg": "Send the PO number."})
        move = self.env["account.move"].create({"move_type": "out_invoice", "partner_id": partner.id})
        self.assertEqual(move.partner_invoice_warning, "Send the PO number.")

    def test_the_switch_and_the_native_blocking_choice_stay_in_sync(self):
        partner = self.env["res.partner"].create({"name": "Native", "sale_warn": "block", "sale_warn_msg": "Native block."})
        self.assertTrue(partner.sale_block)
        with self.assertRaises(ValidationError):
            self.sale(partner)
        partner.sale_block = False
        self.assertEqual(partner.sale_warn, "warning")
        self.assertTrue(self.sale(partner))
        self.product.product_tmpl_id.sale_line_block = True
        self.assertEqual(self.product.product_tmpl_id.sale_line_warn, "block")

    def test_a_blocked_contact_cannot_be_posted_after_the_draft(self):
        partner = self.env["res.partner"].create({"name": "Later"})
        move = self.env["account.move"].create({"move_type": "out_invoice", "partner_id": partner.id,
                                                "invoice_line_ids": [(0, 0, {"name": "Line", "quantity": 1, "price_unit": 10})]})
        partner.invoice_block = True
        with self.assertRaises(ValidationError):
            move.action_post()
        self.assertEqual(move.state, "draft")

    def test_journal_entries_are_never_blocked(self):
        self.fine.write({"invoice_block": True})
        entry = self.env["account.move"].create({"move_type": "entry", "partner_id": self.fine.id})
        self.assertTrue(entry)
