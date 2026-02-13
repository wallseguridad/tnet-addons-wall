# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    l10n_ar_use_manual_rate = fields.Boolean(string="Manual Rate?", default=False)

    def _get_rates(self, company, date):
        """Override to support manual currency rates from context."""
        res = super()._get_rates(company, date)

        currency_manual_rates = self.env.context.get("currency_manual_rates") or {}
        if not currency_manual_rates:
            return res

        # currency_manual_rates: {currency_id: direct_rate}
        # _get_rates() expects inverse -> store 1 / direct_rate
        for currency_id, manual_rate in currency_manual_rates.items():
            if currency_id in res and manual_rate and manual_rate > 0.0:
                res[currency_id] = 1.0 / manual_rate

        return res

    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        """
        Ensure manual rates affect conversions used by sale.order.currency_rate
        and currency._convert().
        """
        rate = super()._get_conversion_rate(from_currency, to_currency, company, date)

        currency_manual_rates = self.env.context.get("currency_manual_rates") or {}
        if not currency_manual_rates:
            return rate

        # If a manual rate exists for the target currency, force it.
        # manual_rate is direct; convert to internal convention.
        manual_rate = currency_manual_rates.get(to_currency.id)
        if manual_rate and manual_rate > 0.0:
            # Keep consistent with _get_rates inversion behavior
            # If your business meaning is different, adjust here.
            return 1.0 / manual_rate

        return rate
