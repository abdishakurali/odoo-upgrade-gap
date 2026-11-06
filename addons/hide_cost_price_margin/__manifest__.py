# -*- coding: utf-8 -*-
{
    "name": "Hide Cost Price and Margin",
    "summary": "Hide cost price and sale margin from salespeople and other users who are not managers: "
               "hide product cost on product form and list, hide margin on sales order lines and totals, "
               "hide inventory valuation. Adds one 'Show Cost Price & Margin' group. Free.",
    "version": "18.0.1.0.0",
    "category": "Sales/Sales",
    "author": "Abdishakur Ali",
    "website": "https://franchisetech.ro",
    "support": "info@franchisetech.ro",
    "license": "LGPL-3",
    "depends": ["sale_management", "sale_margin", "stock_account"],
    "data": [
        "security/hide_cost_security.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
}
