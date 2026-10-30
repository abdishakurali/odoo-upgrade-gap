from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sale_line_block = fields.Boolean(string="Block sales", help="This product cannot be added to a sales order while this is ticked.")
    purchase_line_block = fields.Boolean(string="Block purchases", help="This product cannot be added to a purchase order while this is ticked.")

    def _product_block_message(self, kind):
        self.ensure_one()
        if not self[f"{kind}_line_block"]:
            return False
        what = "sales" if kind == "sale" else "purchase"
        message = self[f"{kind}_line_warn_msg"] or self.env._("No reason given.")
        return self.env._("%(name)s is blocked for %(what)s: %(message)s", name=self.display_name, what=what, message=message)
