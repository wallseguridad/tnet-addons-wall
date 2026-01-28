# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    readonly_price_unit = fields.Boolean(string="Readonly Price Unit",
                                         compute='_compute_readonly_price_unit',
                                         default=False)

    @api.depends('product_id')
    def _compute_readonly_price_unit(self):
        for line in self:
            readonly_price_unit = False
            if self.env.user.has_group('wall_user_restrictions.sale_order_readonly_price_unit'):
                readonly_price_unit = True

            line.readonly_price_unit = readonly_price_unit