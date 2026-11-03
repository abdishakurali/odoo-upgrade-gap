{
    "name": "Blocking Warnings for Contacts and Products",
    "version": "16.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Enforce Odoo's Blocking Message on the server: blocked contacts and products cannot reach a sales order, purchase order or invoice",
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
