# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    l10n_ar_price_unit_usd = fields.Float(
        string="Price Unit USD",
        compute="_compute_l10n_ar_price_unit_usd",
        store=True,
        digits=(16, 6),
    )

    @api.depends(
        "price_unit",
        "order_id.state",
        "order_id.currency_id",
        "order_id.company_id",
        "order_id.l10n_ar_currency_rate_ids.manual_rate",
        "order_id.l10n_ar_currency_rate_ids.name",
    )
    def _compute_l10n_ar_price_unit_usd(self):
        """Compute price in USD using manual rates from purchase order."""
        usd = self.env.ref("base.USD", raise_if_not_found=False)
        
        for line in self:
            # Default: 0.0 if we can't compute
            line.l10n_ar_price_unit_usd = 0.0
            
            order = line.order_id
            if not order or not usd:
                continue

            # Get manual rates context from purchase order
            ctx = order._get_currency_manual_rates_context() if hasattr(order, "_get_currency_manual_rates_context") else {}
            line_ctx = line.with_context(**ctx)

            today = fields.Date.context_today(line)
            currency_from = order.currency_id or order.company_id.currency_id

            # If already in USD, no conversion needed
            if currency_from == usd:
                line.l10n_ar_price_unit_usd = line.price_unit
            else:
                # Convert with manual rates injected via context
                line.l10n_ar_price_unit_usd = currency_from._convert(
                    line.price_unit,
                    usd,
                    order.company_id,
                    date=today,
                )

    def _prepare_account_move_line(self, move=False):
        """Prepare invoice line with manual currency rates applied."""
        self.ensure_one()
        order = self.order_id
        ctx = order._get_currency_manual_rates_context() if hasattr(order, "_get_currency_manual_rates_context") else {}
        return super(PurchaseOrderLine, self.with_context(**ctx))._prepare_account_move_line(move)
