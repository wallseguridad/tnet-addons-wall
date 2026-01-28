{
    'name': 'Wall Reports Custom',
    "author": "Valentin Romero, TecnicanetBA",
    'version': '15.0.0.1.0.4',
    'description': """""",
    "summary" : """""",
    "license" : "LGPL-3",
    'depends': [
        'base',
        'sale',
        'stock',
        'sale_stock',
        'stock_account',
        'l10n_ar',
        'l10n_ar_sale'
    ],
    'data': [ 
        'report/sale_order_templates.xml',
        'report/stock_picking_templates.xml',
        'report/account_move_templates.xml',
        'report/sale_order_views.xml',
        'report/stock_picking_views.xml',
        'report/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'category': 'Technical',
}
