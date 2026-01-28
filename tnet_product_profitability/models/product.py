# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    property_profitability_percentage = fields.Float(string='Profitability %', company_dependent=True)

    @api.depends('property_profitability_percentage', 'standard_price', 'property_cost_currency_id')
    @api.onchange('property_profitability_percentage', 'standard_price', 'property_cost_currency_id')
    def _onchange_profitability_percentage(self):
        if self.standard_price and not self.property_profitability_percentage == 0.0:
            price = self.standard_price * (1 + self.property_profitability_percentage / 100)
            currency_from = self.property_cost_currency_id if self.property_cost_currency_id else self.cost_currency_id
            currency_to = self.property_currency_id if self.property_currency_id else self.currency_id
            self.list_price = currency_from._convert(price, currency_to, self.env.company,
                                                     date=fields.Date.context_today(self), round=False)

    @api.depends('list_price', 'property_currency_id')
    @api.onchange('list_price', 'property_currency_id')
    def _onchange_list_price_profitability_percentage(self):
        if self.list_price and not self.property_profitability_percentage == 0.0:
            #price = self.standard_price * (1 + self.property_profitability_percentage / 100)
            currency_from = self.property_cost_currency_id if self.property_cost_currency_id else self.cost_currency_id
            currency_to = self.property_currency_id if self.property_currency_id else self.currency_id
            cost_price = currency_from._convert(self.standard_price, currency_to, self.env.company,
                                                     date=fields.Date.context_today(self), round=False)
            self.property_profitability_percentage = ((self.list_price / cost_price) -1) * 100

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: