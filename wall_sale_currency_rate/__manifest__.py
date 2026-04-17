# -*- coding: utf-8 -*-
{
    'name': 'Wall - Sale Currency Rate Post-Confirm Edit',
    'version': '18.0.1.0.0',
    'summary': 'Permite editar TC y lista de precios en pedidos de venta confirmados',
    'author': 'GauchoCode',
    'website': 'https://www.gauchocode.com',
    'category': 'Sales',
    'depends': [
        'manual_currency_rate_sale',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
