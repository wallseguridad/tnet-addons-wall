# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_ar_currency_rate_ids = fields.One2many(
        comodel_name="l10n.ar.currency.rate",
        inverse_name="sale_order_id",
        string="Currency Rates",
    )


    def _sanitize_currency_rate_commands(self, commands):
        """Drop malformed O2M create commands missing required fields."""
        if not commands:
            return commands

        cleaned = []
        for cmd in commands:
            # cmd = (0, 0, vals) create
            if isinstance(cmd, (list, tuple)) and len(cmd) >= 3 and cmd[0] == 0:
                vals = cmd[2] or {}
                if not vals.get("name"):
                    # Skip phantom line that would violate NOT NULL(name)
                    continue
            cleaned.append(cmd)
        return cleaned

    @api.model_create_multi
    def create(self, vals_list):
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
        if "l10n_ar_currency_rate_ids" in vals:
            vals["l10n_ar_currency_rate_ids"] = self._sanitize_currency_rate_commands(
                vals["l10n_ar_currency_rate_ids"]
            )
        res = super().write(vals)
        if any(k in vals for k in ("partner_id", "company_id", "pricelist_id")):
            for order in self:
                if order.state in ("draft", "sent"):
                    order._l10n_ar_sync_currency_rate_lines()
        return res

    def _l10n_ar_sync_currency_rate_lines(self):
        self.ensure_one()

        currencies = self.env["res.currency"].search([
            ("active", "=", True),
            ("l10n_ar_use_manual_rate", "=", True),
        ]).filtered(lambda c: c != self.company_id.currency_id)

        existing = {r.name.id: r for r in self.l10n_ar_currency_rate_ids}
        commands = []

        # update or remove
        for currency_id, rate_line in existing.items():
            if currency_id not in currencies.ids:
                commands.append((2, rate_line.id, 0))
            else:
                currency = rate_line.name
                commands.append((1, rate_line.id, {
                    "inverse_rate": currency.inverse_rate,
                    "date": currency.date,
                }))

        # add missing
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

    def _get_currency_manual_rates_context(self):
        self.ensure_one()
        manual_rates = {}
        for rate in self.l10n_ar_currency_rate_ids:
            if rate.manual_rate and rate.manual_rate > 0.0:
                manual_rates[rate.name.id] = rate.manual_rate
        if manual_rates:
            return {"currency_manual_rates": manual_rates}
        return {}

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        self.ensure_one()
        # Keep your behavior: store the manual rate for the SO currency on the invoice
        if self.l10n_ar_currency_rate_ids and self.pricelist_id.currency_id:
            rate_line = self.l10n_ar_currency_rate_ids.filtered(
                lambda r: r.name.id == self.pricelist_id.currency_id.id
            )[:1]
            if rate_line:
                vals["l10n_ar_currency_rate"] = rate_line.manual_rate
        return vals

    @api.onchange("pricelist_id")
    def _onchange_l10n_ar_currency_rates(self):
        for order in self:
            if order.state not in ("draft", "sent", "sale"):
                continue

            # Sync rates lines with currencies that have manual-rate enabled
            currencies = order.env["res.currency"].search([
                ("active", "=", True),
                ("l10n_ar_use_manual_rate", "=", True),
            ])

            # Ensure we never add company currency
            currencies = currencies.filtered(lambda c: c != order.company_id.currency_id)

            existing_by_currency = {r.name.id: r for r in order.l10n_ar_currency_rate_ids}
            commands = []

            # Update existing / remove no longer valid
            for currency_id, rate_line in list(existing_by_currency.items()):
                if currency_id not in currencies.ids:
                    commands.append((2, rate_line.id, 0))
                else:
                    currency = rate_line.name
                    commands.append((1, rate_line.id, {
                        "inverse_rate": currency.inverse_rate,
                        "date": currency.date,
                    }))

            # Add missing
            for currency in currencies:
                if currency.id not in existing_by_currency:
                    commands.append((0, 0, {
                        "name": currency.id,
                        "inverse_rate": currency.inverse_rate,
                        "date": currency.date,
                    }))

            if commands:
                order.l10n_ar_currency_rate_ids = commands

            # Apply repricing logic according to state
            ctx = order._get_currency_manual_rates_context()
            order_ctx = order.with_context(**ctx)

            if order.state in ("draft", "sent"):
                order_ctx._l10n_ar_update_currency_rate_prices()
                order.show_update_pricelist = False

            elif order.state == "sale" and order.pricelist_id:
                order_ctx._l10n_ar_apply_sale_state_prices()

    @api.onchange("l10n_ar_currency_rate_ids")
    def _onchange_l10n_ar_currency_rate_ids(self):
        for order in self:
            if not order.order_line:
                continue

            ctx = order._get_currency_manual_rates_context()
            order_ctx = order.with_context(**ctx)

            if order.state in ("draft", "sent"):
                order_ctx._l10n_ar_update_currency_rate_prices()
                order.show_update_pricelist = False
            elif order.state == "sale" and order.pricelist_id:
                order_ctx._l10n_ar_apply_sale_state_prices()

    def action_update_prices(self):
        # Ensure manual rates are applied when user clicks Update Prices
        res = []
        for order in self:
            ctx = order._get_currency_manual_rates_context()
            res.append(super(SaleOrder, order.with_context(**ctx)).action_update_prices())
        return res[0] if len(res) == 1 else True

    # ---------- helpers ----------

    def _l10n_ar_update_currency_rate_prices(self):
        """Draft/Sent: force line repricing using standard onchange-like behavior."""
        self.ensure_one()
        for line in self.order_line.filtered(lambda l: not l.display_type):
            # Try the safest generic path: trigger qty/uom onchange in modern versions
            # If your v18 has a dedicated method for repricing lines, prefer that.
            line._onchange_product_id()
            line._compute_product_uom_qty()

    def _l10n_ar_apply_sale_state_prices(self):
        """Sale: keep your previous logic: store USD base and convert to pricelist currency."""
        self.ensure_one()
        currency_to = self.pricelist_id.currency_id
        usd = self.env.ref("base.USD", raise_if_not_found=False)
        if not usd:
            raise UserError(_("USD currency not found (base.USD)."))

        today = fields.Date.context_today(self)
        for line in self.order_line.filtered(lambda l: not l.display_type):
            if currency_to == usd:
                line.price_unit = line.l10n_ar_price_unit_usd
            else:
                line.price_unit = usd._convert(
                    line.l10n_ar_price_unit_usd,
                    currency_to,
                    self.company_id,
                    date=today,
                )

