# -*- coding: utf-8 -*-
# Módulo shim v15→v18.
# Existe solo para que Odoo lo trate como upgrade (no fresh install)
# y ejecute los scripts de migrations/. Una vez estable en prod,
# marcar installable=False y sacar del addons path.
{
    'name': 'tnet Product Multi Currency (migration shim)',
    'version': '18.0.1.0.0',
    'author': 'GauchoCode',
    'license': 'LGPL-3',
    'depends': ['product_multi_currency'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
