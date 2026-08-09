# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    lst_price = fields.Float(string='List Price', related='product_id.lst_price', readonly=True, store=True)
    property_currency_id = fields.Many2one(comodel_name='res.currency',
                                           string='Currency',
                                           related='product_id.property_currency_id',
                                           readonly=True,
                                           store=True)
