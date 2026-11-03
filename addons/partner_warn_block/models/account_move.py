from odoo import api, fields, models
from odoo.exceptions import ValidationError

INVOICE_TYPES = ("out_invoice", "out_refund", "in_invoice", "in_refund")


class AccountMove(models.Model):
    _inherit = "account.move"

    partner_invoice_warning = fields.Text(compute="_compute_partner_invoice_warning", string="Contact warning")

    @api.depends("partner_id", "move_type")
    def _compute_partner_invoice_warning(self):
        for move in self:
            partner = move.partner_id.commercial_partner_id
            show = move.move_type in INVOICE_TYPES and partner and partner.invoice_warn not in (False, "no-message")
            move.partner_invoice_warning = partner.invoice_warn_msg if show else False

    @api.constrains("partner_id", "move_type")
    def _check_partner_not_blocked(self):
        for move in self:
            if move.move_type not in INVOICE_TYPES or not move.partner_id:
                continue
            message = move.partner_id._blocking_message("invoice", move)
            if message:
                raise ValidationError(message)

    def action_post(self):
        for move in self:
            if move.move_type in INVOICE_TYPES and move.partner_id:
                message = move.partner_id._blocking_message("invoice", move)
                if message:
                    raise ValidationError(message)
        return super().action_post()
