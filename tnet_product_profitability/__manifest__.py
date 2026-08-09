# -*- coding: utf-8 -*-

{
    'name': 'TNET Product Profitability',
    'version': '18.0.2.0.0',
    'description': """Calculate profitability from cost for a product""",
    'summary': "Calculate profitability from cost for a product",
    'author' : 'Luis Trajtenberg',
    'category' : 'Inventory/Inventory',
    'website': 'https://www.tecnicanet.com',
    'depends': ['base', 'product', 'tnet_product_multi_currency'],
    'demo': [],
    'data': ['views/product_views.xml',
              'security/ir.model.access.csv',
              'security/security.xml'],
    'qweb': [],
    'license': 'LGPL-3',
    'auto_install': False,
    'installable': True,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
