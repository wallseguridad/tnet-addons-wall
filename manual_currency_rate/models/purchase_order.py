# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    l10n_ar_currency_rate_ids = fields.One2many(
        comodel_name="l10n.ar.currency.rate.purchase",
        inverse_name="purchase_order_id",
        string="Currency Rates",
    )

    def _get_currency_manual_rates_context(self):
        """Build context dict with manual currency rates for conversions."""
        self.ensure_one()
        manual_rates = {}
        for rate in self.l10n_ar_currency_rate_ids:
            # Only use manual rate if explicitly set and positive
            if rate.manual_rate and rate.manual_rate > 0.0:
                manual_rates[rate.name.id] = rate.manual_rate
        return {"currency_manual_rates": manual_rates} if manual_rates else {}

    def _sanitize_currency_rate_commands(self, commands):
        """Remove malformed O2M create commands missing required 'name' field."""
        if not commands:
            return commands
        
        cleaned = []
        for cmd in commands:
            # cmd format: (operation_code, id, values_dict)
            # 0 = create, 1 = update, 2 = delete
            if isinstance(cmd, (list, tuple)) and len(cmd) >= 3 and cmd[0] == 0:
                vals = cmd[2] or {}
                if not vals.get("name"):
                    # Skip phantom creates without currency (would violate NOT NULL)
                    continue
            cleaned.append(cmd)
        return cleaned

    @api.model_create_multi
    def create(self, vals_list):
        """Create purchase orders with sanitized currency rate lines."""
        for vals in vals_list:
            if "l10n_ar_currency_rate_ids" in vals:
                vals["l10n_ar_currency_rate_ids"] = self._sanitize_currency_rate_commands(
                    vals["l10n_ar_currency_rate_ids"]
                )
        orders = super().create(vals_list)
        for order in orders:
            order._l10n_ar_sync_currency_rate_lines()
        return orders

    def write(self, vals):
        """Update purchase orders, syncing rates when relevant fields change."""
        if "l10n_ar_currency_rate_ids" in vals:
            vals["l10n_ar_currency_rate_ids"] = self._sanitize_currency_rate_commands(
                vals["l10n_ar_currency_rate_ids"]
            )
        res = super().write(vals)
        # Re-sync rates if currency, company, or partner changed (in draft state)
        if any(k in vals for k in ("currency_id", "company_id", "partner_id")):
            for order in self:
                if order.state in ("draft", "sent", "to approve"):
                    order._l10n_ar_sync_currency_rate_lines()
        return res

    def _l10n_ar_sync_currency_rate_lines(self):
        """Auto-sync currency rate lines based on active currencies marked for manual rates."""
        self.ensure_one()

        # Find all currencies marked for manual rates (except company currency)
        currencies = self.env["res.currency"].search([
            ("active", "=", True),
            ("l10n_ar_use_manual_rate", "=", True),
        ]).filtered(lambda c: c != self.company_id.currency_id)

        # Build dict of existing rates
        existing = {r.name.id: r for r in self.l10n_ar_currency_rate_ids}
        commands = []

        # Update or delete existing rate lines
        for currency_id, rate_line in existing.items():
            if currency_id not in currencies.ids:
                # Currency no longer marked for manual rates → delete line
                commands.append((2, rate_line.id, 0))
            else:
                # Currency still active → update line with fresh Odoo rates
                currency = rate_line.name
                commands.append((1, rate_line.id, {
                    "inverse_rate": currency.inverse_rate,
                    "date": currency.date,
                }))

        # Add new rate lines for currencies not yet in this order
        for currency in currencies:
            if currency.id not in existing:
                commands.append((0, 0, {
                    "name": currency.id,
                    "inverse_rate": currency.inverse_rate,
                    "date": currency.date,
                    "manual_rate": 0.0,
                }))

        if commands:
            self.l10n_ar_currency_rate_ids = commands

    def _prepare_invoice(self):
        """Override to pass manual currency rates to invoice creation."""
        self.ensure_one()
        ctx = self._get_currency_manual_rates_context()
        vals = super(PurchaseOrder, self.with_context(**ctx))._prepare_invoice()
        
        # Preserve manual rate on the invoice if one exists
        rate_line = self.l10n_ar_currency_rate_ids.filtered(
            lambda r: r.name.id == self.currency_id.id
        )[:1]
        if rate_line:
            vals["l10n_ar_currency_rate"] = rate_line.manual_rate
        return vals
