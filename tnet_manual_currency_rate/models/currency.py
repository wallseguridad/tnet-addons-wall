# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCurrency(models.Model):
    _inherit = "res.currency"

    l10n_ar_use_manual_rate = fields.Boolean('Manual Rate?', default=False)

    def _get_rates(self, company, date):
        res = super(ResCurrency, self)._get_rates(company, date)
        currency_manual_rates = self.env.context.get('currency_manual_rates', False)
        if currency_manual_rates:
            for currency_id, manual_rate in currency_manual_rates.items():
                if currency_id in res:
                    res[currency_id] = 1 / manual_rate
        return res