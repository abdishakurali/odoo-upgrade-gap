from odoo import _, api, fields, models

KINDS = {"sale": "sales orders", "purchase": "purchase orders", "invoice": "invoices"}


class ResPartner(models.Model):
    _inherit = "res.partner"

    # On this series Odoo still has the "Blocking Message" choice (sale_warn / purchase_warn / invoice_warn = 'block'),
    # but it only acts in the form (onchange). These switches mirror that choice and the checks of this module enforce it
    # on the server: on create, on write, on confirmation and on posting, whatever the entry point (import, API, code).
    sale_block = fields.Boolean(string="Block sales", compute="_compute_blocks", inverse="_inverse_sale_block", store=True,
                                help="Nobody can create a sales order for this contact (or its company) while this is ticked.")
    purchase_block = fields.Boolean(string="Block purchases", compute="_compute_blocks", inverse="_inverse_purchase_block", store=True,
                                    help="Nobody can create a purchase order for this contact (or its company) while this is ticked.")
    invoice_block = fields.Boolean(string="Block invoices", compute="_compute_blocks", inverse="_inverse_invoice_block", store=True,
                                   help="Nobody can create an invoice or bill for this contact (or its company) while this is ticked.")

    @api.depends("sale_warn", "purchase_warn", "invoice_warn")
    def _compute_blocks(self):
        for partner in self:
            partner.sale_block = partner.sale_warn == "block"
            partner.purchase_block = partner.purchase_warn == "block"
            partner.invoice_block = partner.invoice_warn == "block"

    def _set_block(self, kind):
        for partner in self:
            if partner[f"{kind}_block"]:
                if partner[f"{kind}_warn"] != "block":
                    partner[f"{kind}_warn"] = "block"
            elif partner[f"{kind}_warn"] == "block":
                partner[f"{kind}_warn"] = "warning" if partner[f"{kind}_warn_msg"] else "no-message"

    def _inverse_sale_block(self):
        self._set_block("sale")

    def _inverse_purchase_block(self):
        self._set_block("purchase")

    def _inverse_invoice_block(self):
        self._set_block("invoice")

    def _blocking_message(self, kind, record=None):
        """The reason why this contact is blocked for *kind* ('sale', 'purchase' or 'invoice'), or False when it is not.

        The company a contact belongs to decides, so a contact of a blocked company is blocked too. Other modules extend this
        method (and `_block_overridden`) to add rules or to allow an authorised override."""
        self.ensure_one()
        partner = self.commercial_partner_id or self
        if not partner[f"{kind}_block"]:
            return False
        if self._block_overridden(kind, record):
            return False
        message = partner[f"{kind}_warn_msg"] or _("No reason given.")
        return _("%(name)s is blocked for %(what)s: %(message)s", name=partner.display_name, what=KINDS[kind], message=message)

    @api.model
    def _block_overridden(self, kind, record=None):
        """Extension point: True when an authorised user explicitly lets this record through."""
        return False
