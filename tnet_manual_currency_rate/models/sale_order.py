# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_ar_currency_rate_ids = fields.One2many(comodel_name='l10n.ar.currency.rate', inverse_name="sale_order_id", string="Currency Rates")

    def context_manual_rate(self):
        context = dict(self.env.context)
        if self.l10n_ar_currency_rate_ids:

            currency_manual_rates = {}
            for l10n_ar_currency_rate_id in self.l10n_ar_currency_rate_ids:
                if (l10n_ar_currency_rate_id.manual_rate
                    and l10n_ar_currency_rate_id.manual_rate != l10n_ar_currency_rate_id.inverse_rate):
                    currency_manual_rates[l10n_ar_currency_rate_id.name.id] = l10n_ar_currency_rate_id.manual_rate

            if currency_manual_rates:
                context['currency_manual_rates'] = currency_manual_rates

        return context

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.l10n_ar_currency_rate_ids:
            for l10n_ar_currency_rate_id in self.l10n_ar_currency_rate_ids:
                if l10n_ar_currency_rate_id.name.id == self.pricelist_id.currency_id.id:
                    res['l10n_ar_currency_rate'] = l10n_ar_currency_rate_id.manual_rate
                    break
        return res

    @api.onchange('pricelist_id', 'order_line')
    def _onchange_pricelist_id(self):
        self.show_update_pricelist = False
        #if self.order_line and self.pricelist_id and self._origin.pricelist_id != self.pricelist_id:
            #self.show_update_pricelist = True
        #else:
            #self.show_update_pricelist = False

    @api.onchange('pricelist_id')
    def _onchange_l10n_ar_currency_rates(self):
        if self.state in ['draft', 'sent']:
            currency_model = self.env['res.currency']
            currency_ids = currency_model.search([('active', '=', True), ('l10n_ar_use_manual_rate', '=', True)])
            currency_rates = []
            if not self.l10n_ar_currency_rate_ids:
                if currency_ids:
                    for currency_id in currency_ids:
                        if currency_id != self.env.company.currency_id:
                            currency_rates.append((0, 0, {'name': currency_id.id,
                                                          'inverse_rate': currency_id.inverse_rate,
                                                          'date': currency_id.date}))

                    self.l10n_ar_currency_rate_ids = currency_rates
            else:
                currency_manual_rate_ids = []
                for l10n_ar_currency_id in self.l10n_ar_currency_rate_ids:
                    currency_manual_rate_ids.append(l10n_ar_currency_id.name.id)
                    if l10n_ar_currency_id.name.id in currency_ids.ids:
                        l10n_ar_currency_id.inverse_rate = l10n_ar_currency_id.name.inverse_rate
                        l10n_ar_currency_id.date = l10n_ar_currency_id.name.date
                    else:
                        l10n_ar_currency_id.unlink()

                if currency_ids:
                    for currency_id in currency_ids:
                        if currency_id.id not in currency_manual_rate_ids and currency_id != self.env.company.currency_id:
                            currency_rates.append((0, 0, {'name': currency_id.id,
                                                          'inverse_rate': currency_id.inverse_rate,
                                                          'date': currency_id.date}))

                    self.l10n_ar_currency_rate_ids = currency_rates

            self.env.context = self.context_manual_rate()
            self.update_currency_rate_prices()
            self.show_update_pricelist = False
        elif self.state in ['sale']:
            if self.pricelist_id:
                self.env.context = self.context_manual_rate()
                currency_to = self.pricelist_id.currency_id
                for line in self.order_line:
                    if currency_to.name == 'USD':
                        line.price_unit = line.l10n_ar_price_unit_usd
                    else:
                        line.price_unit = self.env.ref('base.USD')._convert(line.l10n_ar_price_unit_usd, currency_to,
                                                                            self.company_id,
                                                                            date=fields.Date.context_today(self))


    @api.onchange('l10n_ar_currency_rate_ids')
    def _onchange_l10n_ar_currency_rate(self):
        if self.order_line:
            self.env.context = self.context_manual_rate()
            if self.state in ['draft', 'sent']:
                self.update_currency_rate_prices()
            elif self.state in ['sale']:
                currency_to = self.pricelist_id.currency_id
                for line in self.order_line:
                    if currency_to.name == 'USD':
                        line.price_unit = line.l10n_ar_price_unit_usd
                    else:
                        line.price_unit = self.env.ref('base.USD')._convert(line.l10n_ar_price_unit_usd, currency_to,
                                                                            self.company_id,
                                                                            date=fields.Date.context_today(self))


    def update_prices(self):
        self.env.context = self.context_manual_rate()
        return super(SaleOrder, self).update_prices()

    def update_currency_rate_prices(self):
        self.ensure_one()
        for line in self._get_update_prices_lines():
            line.product_uom_change()
            line.discount = 0  # Force 0 as discount for the cases when _onchange_discount directly returns
            line._onchange_discount()
        self.show_update_pricelist = False

class l10narCurrencyRate(models.Model):
    _name = 'l10n.ar.currency.rate'
    _description = 'l10n ar Currency Rate'
    _order = 'name asc'

    name = fields.Many2one(comodel_name='res.currency', string='Currency')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order', ondelete='restrict')
    inverse_rate = fields.Float('Odoo Rate')
    manual_rate = fields.Float('Manual Rate', default=0.0)
    date = fields.Date('Date Rate')

    @api.onchange('manual_rate')
    def _onchange_manual_rate(self):
        if self.manual_rate < 0.0:
            return {'warning': {'title': _('Input Error'),
                                'message': _('The manual rate value must be greater than or equal to 0.0')}}
