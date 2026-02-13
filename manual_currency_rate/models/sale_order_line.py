# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    l10n_ar_price_unit_usd = fields.Float(
        string="Price Unit USD",
        compute="_compute_l10n_ar_price_unit_usd",
        store=True,
        digits=(16, 6),
    )

    @api.depends(
        "price_unit",
        "order_id.state",
        "order_id.pricelist_id",
        "order_id.pricelist_id.currency_id",
        "order_id.company_id",
        "order_id.l10n_ar_currency_rate_ids.manual_rate",
        "order_id.l10n_ar_currency_rate_ids.name",
    )
    def _compute_l10n_ar_price_unit_usd(self):
        usd = self.env.ref("base.USD", raise_if_not_found=False)

        for line in self:
            # Default: keep previous stored value if we can't compute
            price_usd = line.l10n_ar_price_unit_usd

            order = line.order_id
            if not order or not usd:
                line.l10n_ar_price_unit_usd = price_usd
                continue

            # Apply manual rates through context (do NOT mutate env.context)
            ctx = order._get_currency_manual_rates_context() if hasattr(order, "_get_currency_manual_rates_context") else {}
            line_ctx = line.with_context(**ctx)

            if order.state in ("draft", "sent"):
                currency_from = order.pricelist_id.currency_id or order.company_id.currency_id
                if currency_from == usd:
                    price_usd = line.price_unit
                else:
                    price_usd = currency_from._convert(
                        line.price_unit,
                        usd,
                        order.company_id,
                        date=fields.Date.context_today(line),
                    )

            line_ctx.l10n_ar_price_unit_usd = price_usd
