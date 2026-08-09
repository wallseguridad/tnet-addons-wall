# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    l10n_ar_currency_rate_ids = fields.One2many(comodel_name='l10n.ar.currency.rate.purchase', inverse_name="purchase_order_id", string="Currency Rates")

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

    @api.onchange('l10n_ar_currency_rate_ids')
    def _onchange_l10n_ar_currency_rate(self):
        if self.order_line:
            self.env.context = self.context_manual_rate()
            for line in self.order_line:
                #if line.order_id.state in ['draft', 'sent', 'to approve']:
                    #line.l10n_ar_price_unit_usd = self.currency_id._convert(line.price_unit, self.env.ref('base.USD'),
                                                                            #self.company_id,
                                                                            #date=fields.Date.context_today(self))
                line.l10n_ar_price_unit_usd = self.currency_id._convert(line.price_unit, self.env.ref('base.USD'),
                                                                        self.company_id,
                                                                        date=fields.Date.context_today(self))
        #if self.order_line:
            #self.env.context = self.context_manual_rate()
            #for line in self.order_line:
                #if line.order_id.state in ['draft', 'sent', 'to approve']:
                    #line._onchange_quantity()
                #else:
                    #line.price_unit = self.env.ref('base.USD')._convert(line.l10n_ar_price_unit_usd, self.currency_id,
                                                                        #self.company_id,
                                                                        #date=fields.Date.context_today(self))

    @api.depends('date_order', 'currency_id', 'company_id', 'company_id.currency_id')
    def _compute_currency_rate(self):
        self.env.context = self.context_manual_rate()
        for order in self:
            if order.state in ['draft', 'sent', 'to approve']:
                return super(PurchaseOrder, order)._compute_currency_rate()

    @api.onchange('currency_id')
    def _onchange_l10n_ar_currency_rates(self):
        if self.state in ['draft', 'sent', 'to approve']:
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
            self._onchange_l10n_ar_currency_rate()
        elif self.state in ['purchase']:
            self.env.context = self.context_manual_rate()
            currency_order_id = self.currency_id
            for line in self.order_line:
                if currency_order_id.name == 'USD':
                    line.price_unit =  line.l10n_ar_price_unit_usd
                else:
                    line.price_unit = self.env.ref('base.USD')._convert(line.l10n_ar_price_unit_usd, currency_order_id,
                                                                        self.company_id,
                                                                        date=fields.Date.context_today(self))
    def _add_supplier_to_product(self):
        self.env.context = self.context_manual_rate()
        return super(PurchaseOrder, self)._add_supplier_to_product()

    def _approval_allowed(self):
        self.env.context = self.context_manual_rate()
        return super(PurchaseOrder, self)._approval_allowed()

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        if self.l10n_ar_currency_rate_ids:
            for l10n_ar_currency_rate_id in self.l10n_ar_currency_rate_ids:
                if l10n_ar_currency_rate_id.name.id == self.currency_id.id:
                    res['l10n_ar_currency_rate'] = l10n_ar_currency_rate_id.manual_rate
                    break
        return res

    def _prepare_supplier_info(self, partner, line, price, currency):
        # Prepare supplierinfo data when adding a product
        res = super(PurchaseOrder, self)._prepare_supplier_info(partner, line, price, currency)
        #return {
            #'name': partner.id,
            #'sequence': max(line.product_id.seller_ids.mapped('sequence')) + 1 if line.product_id.seller_ids else 1,
            #'min_qty': 0.0,
            #'price': price,
            #'currency_id': currency.id,
            #'delay': 0,
        #}
        return res


class l10narCurrencyRatePurchase(models.Model):
    _name = 'l10n.ar.currency.rate.purchase'
    _description = 'l10n ar Currency Rate'
    _order = 'name asc'

    name = fields.Many2one(comodel_name='res.currency', string='Currency')
    purchase_order_id = fields.Many2one(comodel_name='purchase.order', string='Purchase Order', ondelete='restrict')
    inverse_rate = fields.Float('Odoo Rate')
    manual_rate = fields.Float('Manual Rate', default=0.0)
    date = fields.Date('Date Rate')

    @api.onchange('manual_rate')
    def _onchange_manual_rate(self):
        if self.manual_rate < 0.0:
            return {'warning': {'title': _('Input Error'),
                                'message': _('The manual rate value must be greater than or equal to 0.0')}}