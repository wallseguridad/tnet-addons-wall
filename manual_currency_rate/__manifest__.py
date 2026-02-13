# -*- coding: utf-8 -*-

{
    'name': "TNET Manual Currency Rate",
    'version': '18.0.1.0.1',
    'description': """Manual Currency Rate in Sale Orders""",
    'summary': "Manual Currency Rate in Sale Orders",
    'author': 'GauchoCode',
    'website': 'https://www.gauchocode.com',
    'category': "Localization/Argentina",
    'depends': ['base', 'sale', 'purchase', 'l10n_ar', 'l10n_ar_ux', 'account_ux'],
    'data': [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/currency_views.xml",
        "views/purchase_order_views.xml",
        "views/sale_order_views.xml",
        #"views/account_move_views.xml",
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}