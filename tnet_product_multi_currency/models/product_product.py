# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import float_compare


class ProductProduct(models.Model):
    _inherit = 'product.product'

    wall_cost = fields.Float(string='Wall Cost',
                             company_dependent=True,
                             digits='Product Price',
                             groups='base.group_user',
                             help="Cost expressed in the product Cost Currency. The standard price is "
                                  "recomputed daily from this value at the current exchange rate.")

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products.filtered('wall_cost')._update_standard_price_from_wall_cost()
        return products

    def write(self, vals):
        res = super().write(vals)
        if 'wall_cost' in vals:
            self._update_standard_price_from_wall_cost()
        return res

    def _update_standard_price_from_wall_cost(self, date=None):
        """Set standard_price = wall_cost converted to the company currency at the given date's rate.

        Writing standard_price goes through stock_account, so a revaluation layer is created
        for products with stock (and a journal entry if the valuation is automated).
        Products without wall_cost are left untouched.
        """
        company = self.env.company
        date = date or fields.Date.context_today(self)
        precision = self.env['decimal.precision'].precision_get('Product Price')
        for product in self:
            if not product.wall_cost:
                continue
            currency = product.property_cost_currency_id or company.currency_id
            new_price = currency._convert(product.wall_cost, company.currency_id, company, date, round=False)
            if float_compare(new_price, product.standard_price, precision_digits=precision):
                product.standard_price = new_price

    @api.model
    def _cron_update_standard_price_from_wall_cost(self):
        for company in self.env['res.company'].search([]):
            products = self.with_company(company).search([('wall_cost', '!=', 0)])
            products._update_standard_price_from_wall_cost()
