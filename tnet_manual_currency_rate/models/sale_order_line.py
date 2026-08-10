# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    l10n_ar_price_unit_usd = fields.Float(string='Price Unit USD', compute='_compute_l10n_ar_price_unit_usd', store=True, digits=(16, 6))

    # product_id_change/product_uom_change ya no existen en v18 (sale.order.line
    # pasó a precios por @api.depends, ver _compute_price_unit). Solo inyectaban
    # el contexto de tasa manual antes de recomputar precios; ese contexto ya lo
    # setea sale_order.py._onchange_l10n_ar_currency_rates() antes de llamar a
    # update_currency_rate_prices(), así que no hace falta repetirlo acá.

    @api.depends('price_unit')
    def _compute_l10n_ar_price_unit_usd(self):
        self.env.context = self.order_id.context_manual_rate()

        for line in self:
            price_usd = line.l10n_ar_price_unit_usd
            if line.order_id.state in ['draft', 'sent']:
                currency_from = line.order_id.pricelist_id.currency_id
                if currency_from.name == 'USD':
                    price_usd =  line.price_unit
                else:
                    price_usd = currency_from._convert(line.price_unit, self.env.ref('base.USD'), self.company_id,
                                                        date=fields.Date.context_today(self))

            line.l10n_ar_price_unit_usd = price_usd
