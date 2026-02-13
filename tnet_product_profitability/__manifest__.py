# -*- coding: utf-8 -*-

{
    'name' : 'TNET Product Profitability',
    'version' : '18.0.1.0.1',
    'description': """Calculate profitability from cost for a product""",
    'summary': "Calculate profitability from cost for a product",
    'author' : 'GauchoCode',
    'category' : 'Inventory/Inventory',
    'website': 'https://www.gauchocode.com',
    'depends' : ['base', 'product', 'tnet_product_multi_currency'],
    'demo' : [],
    'data' : ['views/product_views.xml',
              'security/ir.model.access.csv',
              'security/security.xml'],
    'qweb': [],
    'license': 'LGPL-3',
    'auto_install': False,
    'installable': True,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
