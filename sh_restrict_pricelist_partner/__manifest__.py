# -*- coding: utf-8 -*-
{
    "name": "Restrict Pricelist For customer",

    "author": "Softhealer Technologies",

    "license": "OPL-1",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "version": "15.0.2",

    "category": "Sales",

    "summary": "Customer Restrict Price list, Client Restrict Pricelist, Restrict Pricelist Customer,  Pricelist Security App, Pricelist Allocation Module, Customer Pricelist, Pricelist Visiblity Odoo",

    "description": """Currently in odoo customers can access all pricelists by default. So this module restricts pricelists for the customer. This module displays the selected pricelists to the customer. You need to go inside the particular customer and select the pricelist, which pricelist you want to visible. if you don't give any pricelist than all pricelist will be accessible/visible. wherever the pricelist field of view it will affect all those fields. Cheers! """,

    "depends":  [
        'sale_management'
    ],

    "data": [
            "views/pricelist_access.xml",
    ],
    "images": ["static/description/background.png", ],

    "installable": True,
    "application": True,
    "auto_install": False,
    "price": 25,
    "currency": "EUR"
}
