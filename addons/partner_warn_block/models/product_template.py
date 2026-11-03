from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Mirrors Odoo's own "Blocking Message" choice on the product (sale_line_warn / purchase_line_warn = 'block').
    sale_line_block = fields.Boolean(string="Block sales", compute="_compute_line_blocks", inverse="_inverse_sale_line_block", store=True,
                                     help="This product cannot be added to a sales order while this is ticked.")
    purchase_line_block = fields.Boolean(string="Block purchases", compute="_compute_line_blocks", inverse="_inverse_purchase_line_block", store=True,
                                         help="This product cannot be added to a purchase order while this is ticked.")

    @api.depends("sale_line_warn", "purchase_line_warn")
    def _compute_line_blocks(self):
        for template in self:
            template.sale_line_block = template.sale_line_warn == "block"
            template.purchase_line_block = template.purchase_line_warn == "block"

    def _set_line_block(self, kind):
        for template in self:
            if template[f"{kind}_line_block"]:
                if template[f"{kind}_line_warn"] != "block":
                    template[f"{kind}_line_warn"] = "block"
            elif template[f"{kind}_line_warn"] == "block":
                template[f"{kind}_line_warn"] = "warning" if template[f"{kind}_line_warn_msg"] else "no-message"

    def _inverse_sale_line_block(self):
        self._set_line_block("sale")

    def _inverse_purchase_line_block(self):
        self._set_line_block("purchase")

    def _product_block_message(self, kind):
        self.ensure_one()
        if not self[f"{kind}_line_block"]:
            return False
        what = "sales" if kind == "sale" else "purchase"
        message = self[f"{kind}_line_warn_msg"] or _("No reason given.")
        return _("%(name)s is blocked for %(what)s: %(message)s", name=self.display_name, what=what, message=message)
