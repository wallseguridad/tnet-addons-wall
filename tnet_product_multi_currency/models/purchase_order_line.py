# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    standard_price = fields.Float(string='Standard Price',
                                  related='product_id.standard_price',
                                  readonly=True,
                                  store=True)
    wall_cost = fields.Float(string='Wall Cost',
                             related='product_id.wall_cost',
                             readonly=True,
                             store=True)
    cost_currency_id = fields.Many2one(comodel_name='res.currency',
                                       string='Currency',
                                       related='product_id.property_cost_currency_id',
                                       readonly =True,
                                       store=True)
