{
    "name": "Block Customers and Products",
    "version": "16.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Blocking message enforced on the server for Odoo 16: block customer, block vendor and block product for real, also through import, the API, confirming a quotation and posting an invoice. Standard Odoo applies the blocking message only in the form. Free. Not a credit limit check: to block customers with overdue invoices automatically, add the paid Pro version (partner_warn_block_pro).",
    "description": "In Odoo 16 the Blocking Message choice only acts in the form. This module enforces it on the server: a blocked contact "
    "cannot be saved on a sales order, purchase order or invoice (also through import or the API), a quotation or bill cannot be confirmed "
    "or posted once the contact is blocked, and a blocked product cannot be put on an order line.",
    "author": "Abdishakur Ali",
    "maintainer": "Abdishakur Ali <info@franchisetech.ro>",
    "website": "https://apps.odoo.com/apps/modules/browse?author=Abdishakur%20Ali",
    "license": "LGPL-3",
    "depends": ["sale", "purchase", "account"],
    "data": [
        "views/account_move_views.xml",
    ],
    "images": [
        "static/description/banner.png",
        "static/description/screenshots/01-block-a-contact.jpg",
        "static/description/screenshots/02-the-order-is-stopped.jpg",
        "static/description/screenshots/03-recalled-product.jpg",
        "static/description/screenshots/04-invoice-reminder.jpg",
    ],
    "application": False,
    "installable": True,
}
