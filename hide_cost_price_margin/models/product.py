# -*- coding: utf-8 -*-
from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _price_compute(self, price_type, *args, **kwargs):
        # Pricelists based on cost must keep working for users who may not read the cost (strict mode).
        if price_type == 'standard_price' and not self.env.su:
            return super(ProductTemplate, self.sudo())._price_compute(price_type, *args, **kwargs)
        return super()._price_compute(price_type, *args, **kwargs)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _price_compute(self, price_type, *args, **kwargs):
        if price_type == 'standard_price' and not self.env.su:
            return super(ProductProduct, self.sudo())._price_compute(price_type, *args, **kwargs)
        return super()._price_compute(price_type, *args, **kwargs)
