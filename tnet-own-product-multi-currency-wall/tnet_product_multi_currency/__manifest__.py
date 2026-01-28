# -*- coding: utf-8 -*-

{
    'name': "TNET Product Multi Currency",
    'version': '15.0.4',
    'description': """Product Multi Currency""",
    'summary': "Product Multi Currency",
    'author': 'Luis Trajtenberg',
    'website': 'https://www.tecnicanet.com',
    'category': "Inventory/Inventory",
    'depends': ['product', 'sale', 'purchase'],
    'data': [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/purchase_order_views.xml",
        "views/sale_order_views.xml",
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}