# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class L10nArCurrencyRate(models.Model):
    """Transient model to hold manual currency rates for sale orders."""
    
    _name = "l10n.ar.currency.rate"
    _description = "Manual Currency Rate (Sale)"
    _order = "name asc"

    name = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        ondelete="cascade",
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        required=True,
        ondelete="cascade",
    )
    inverse_rate = fields.Float(
        string="Odoo Rate",
        help="Current rate from Odoo (read-only)",
    )
    manual_rate = fields.Float(
        string="Manual Rate",
        default=0.0,
        help="Override rate set by user",
    )
    date = fields.Date(
        string="Date Rate",
        help="Date of the currency rate",
    )

    @api.onchange("manual_rate")
    def _onchange_manual_rate(self):
        """Validate that manual rate is non-negative."""
        if self.manual_rate < 0.0:
            return {
                "warning": {
                    "title": _("Input Error"),
                    "message": _("Manual rate must be greater than or equal to 0.0"),
                }
            }
