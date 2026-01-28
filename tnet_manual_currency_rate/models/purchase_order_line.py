# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang, get_lang, format_amount


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    l10n_ar_price_unit_usd = fields.Float(string='Price Unit USD', compute='_compute_l10n_ar_price_unit_usd', store=True, digits=(16, 6))

    @api.depends('price_unit')
    def _compute_l10n_ar_price_unit_usd(self):
        for line in self:
            price_usd = line.l10n_ar_price_unit_usd
            if line.order_id.state in ['draft', 'sent', 'to approve']:
                self.env.context = line.order_id.context_manual_rate()
                currency_order_id = line.order_id.currency_id
                if currency_order_id.name == 'USD':
                    price_usd =  line.price_unit
                else:
                    price_usd = currency_order_id._convert(line.price_unit, self.env.ref('base.USD'),
                                                         self.company_id,
                                                         date=fields.Date.context_today(self))

            self.env.context = line.order_id.context_manual_rate()
            currency_order_id = line.order_id.currency_id
            if currency_order_id.name == 'USD':
                price_usd =  line.price_unit
            else:
                price_usd = currency_order_id._convert(line.price_unit, self.env.ref('base.USD'),
                                                     self.company_id,
                                                     date=fields.Date.context_today(self))

            line.l10n_ar_price_unit_usd = price_usd

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        self.env.context = self.order_id.context_manual_rate()
        if not self.product_id or self.invoice_lines:
            return
        params = {'order_id': self.order_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return


        if not self.product_id or self.invoice_lines:
            return
        self.env.context = self.order_id.context_manual_rate()
        params = {'order_id': self.order_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # If not seller, use the standard price. It needs a proper currency conversion.
        if not seller:
            po_line_uom = self.product_uom or self.product_id.uom_po_id
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
                self.product_id.supplier_taxes_id,
                self.taxes_id,
                self.company_id,
            )
            cost_currency_id = self.product_id.property_cost_currency_id if self.product_id.property_cost_currency_id else self.order_id.company_id.currency_id
            if price_unit and self.order_id.currency_id and cost_currency_id != self.order_id.currency_id:
                price_unit = self.product_id.property_cost_currency_id._convert(
                    price_unit,
                    self.order_id.currency_id,
                    self.order_id.company_id,
                    self.date_order or fields.Date.today(),
                )

            self.price_unit = price_unit
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, self.product_id.supplier_taxes_id, self.taxes_id, self.company_id) if seller else 0.0
        if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, self.order_id.currency_id, self.order_id.company_id, self.date_order or fields.Date.today())

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit

        default_names = []
        vendors = self.product_id._prepare_sellers({})
        for vendor in vendors:
            product_ctx = {'seller_id': vendor.id, 'lang': get_lang(self.env, self.partner_id.lang).code}
            default_names.append(self._get_product_purchase_description(self.product_id.with_context(product_ctx)))

        if (self.name in default_names or not self.name):
            product_ctx = {'seller_id': seller.id, 'lang': get_lang(self.env, self.partner_id.lang).code}
            self.name = self._get_product_purchase_description(self.product_id.with_context(product_ctx))

    def action_update_standard_price(self):
        if self.product_id:
            self.product_id.standard_price = self.env.ref('base.USD')._convert(self.l10n_ar_price_unit_usd,
                                                   self.product_id.cost_currency_id,
                                                   self.company_id,
                                                   date=fields.Date.context_today(self))
            if self.product_id.standard_price and not self.product_id.property_profitability_percentage == 0.0:
                price = self.product_id.standard_price * (1 + self.product_id.property_profitability_percentage / 100)
                currency_from = self.product_id.property_cost_currency_id if self.product_id.property_cost_currency_id else self.product_id.cost_currency_id
                currency_to = self.product_id.property_currency_id if self.product_id.property_currency_id else self.product_id.currency_id
                self.product_id.list_price = currency_from._convert(price, currency_to, self.env.company,
                                                                    date=fields.Date.context_today(self), round=False)

    def _prepare_account_move_line(self, move=False):
        self.env.context = self.order_id.context_manual_rate()
        return super(PurchaseOrderLine, self)._prepare_account_move_line(move)

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        self.env.context = self.order_id.context_manual_rate()
        return super(PurchaseOrderLine, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, supplier, po)
