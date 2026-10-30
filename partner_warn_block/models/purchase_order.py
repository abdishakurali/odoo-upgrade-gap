from odoo import api, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange("partner_id")
    def _onchange_partner_block(self):
        for order in self:
            message = order.partner_id._blocking_message("purchase", order) if order.partner_id else False
            if message:
                order.partner_id = False
                return {"warning": {"title": self.env._("Blocked contact"), "message": message}}

    @api.constrains("partner_id")
    def _check_partner_not_blocked(self):
        for order in self:
            message = order.partner_id._blocking_message("purchase", order) if order.partner_id else False
            if message:
                raise ValidationError(message)

    def button_confirm(self):
        for order in self:
            message = order.partner_id._blocking_message("purchase", order) if order.partner_id else False
            if message:
                raise ValidationError(message)
        return super().button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.constrains("product_id")
    def _check_product_not_blocked(self):
        for line in self:
            if line.display_type or not line.product_id:
                continue
            message = line.product_id.product_tmpl_id._product_block_message("purchase")
            if message and not line.order_id.partner_id._block_overridden("purchase", line.order_id):
                raise ValidationError(message)
