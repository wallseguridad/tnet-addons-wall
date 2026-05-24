# -*- coding: utf-8 -*-

{
    'name': "Wall User Restrictrions",
    'version': '18.0.2.0.2',
    'description': """Wall User Restrictrions""",
    'summary': "Wall User Restrictrions",
    'author': 'GauchoCode',
    'website': 'https://www.gauchocode.com',
    'category': "Generic Modules",
    'depends': ['base', 'account', 'sale', 'purchase', 'stock'],
    'data': [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menu_views.xml",
        "views/product_views.xml",
        "views/sale_order_views.xml",
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
