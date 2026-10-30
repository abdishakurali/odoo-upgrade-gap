from odoo import api, fields, models

KINDS = {"sale": "sales orders", "purchase": "purchase orders", "invoice": "invoices"}


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_block = fields.Boolean(string="Block sales", help="Nobody can create a sales order for this contact (or its company) while this is ticked.")
    purchase_block = fields.Boolean(string="Block purchases", help="Nobody can create a purchase order for this contact (or its company) while this is ticked.")
    invoice_block = fields.Boolean(string="Block invoices", help="Nobody can create an invoice or bill for this contact (or its company) while this is ticked.")
    invoice_warn_msg = fields.Text(string="Message for invoices")

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
        message = partner[f"{kind}_warn_msg"] or self.env._("No reason given.")
        return self.env._("%(name)s is blocked for %(what)s: %(message)s", name=partner.display_name, what=KINDS[kind], message=message)

    @api.model
    def _block_overridden(self, kind, record=None):
        """Extension point: True when an authorised user explicitly lets this record through."""
        return False
