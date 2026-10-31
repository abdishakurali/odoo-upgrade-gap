{
    "name": "Blocking Warnings for Contacts and Products",
    "version": "20.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Block sales, purchases and invoices for a contact, and block a product on order lines: the 'Block' option Odoo 19 removed",
    "description": "Odoo 19 kept only the warning message. This module brings back the Block choice of Odoo 18: tick Block next to the message "
    "and the contact cannot be used on a sales order, purchase order or invoice; the same for products on order lines.",
    "author": "Abdishakur Ali",
    "maintainer": "Abdishakur Ali <info@franchisetech.ro>",
    "website": "https://apps.odoo.com/apps/modules/browse?author=Abdishakur%20Ali",
    "license": "LGPL-3",
    "depends": ["sale", "purchase", "account"],
    "data": [
        "views/res_partner_views.xml",
        "views/product_template_views.xml",
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
