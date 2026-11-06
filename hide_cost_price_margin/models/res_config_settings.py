# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hcp_strict_mode = fields.Boolean(
        string='Strict cost hiding',
        config_parameter='hide_cost_price_margin.strict_mode',
        help='Also block cost price and margin fields over the API (read, write, group by), not only in '
             'screens and exports. Other modules that read the cost as the current user may then fail '
             'for users without the "Show Cost Price & Margin" access.',
    )
