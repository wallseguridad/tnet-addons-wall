# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ar_reference_currency_rate = fields.Float(string='Referencia T.C', digits=(16, 6))
    currency_name = fields.Char('Currency Name', related='currency_id.name', readonly=True)

    # Campos base que en v15 venían de los forks Tecnicanet de l10n_ar_ux y
    # account_ux (reemplazados en v18 por los repos oficiales de Adhoc, que
    # no traen esta funcionalidad). Se recrean acá porque tnet_manual_currency_rate
    # depende de ellos.
    other_currency = fields.Boolean(compute='_compute_other_currency')
    computed_currency_rate = fields.Float(
        compute='_compute_currency_rate',
        string='Currency Rate (preview)',
        digits=(16, 6),
    )
    l10n_ar_currency_rate = fields.Float(compute='_compute_l10n_ar_currency_rate', store=True)

    @api.depends('company_currency_id', 'currency_id')
    def _compute_other_currency(self):
        other_currency = self.filtered(lambda x: x.company_currency_id != x.currency_id)
        other_currency.other_currency = True
        (self - other_currency).other_currency = False

    @api.depends('reversed_entry_id')
    def _compute_l10n_ar_currency_rate(self):
        """ Si es una nota de crédito en moneda extranjera y la moneda extranjera es la
        misma que la de la factura original, usamos la tasa de la factura original. """
        ar_reversed_other_currency = self.filtered(
            lambda x: x.is_invoice() and x.reversed_entry_id and
            x.company_id.country_id == self.env.ref('base.ar') and
            x.currency_id != x.company_id.currency_id and
            x.reversed_entry_id.currency_id == x.currency_id)
        self.filtered(lambda x: x.move_type == 'entry').l10n_ar_currency_rate = False
        for rec in ar_reversed_other_currency:
            rec.l10n_ar_currency_rate = rec.reversed_entry_id.l10n_ar_currency_rate

    @api.depends('currency_id', 'company_id', 'date', 'invoice_date')
    def _compute_currency_rate(self):
        need_currency_rate = self.filtered(lambda x: x.currency_id and x.company_id and (x.currency_id != x.company_id.currency_id))
        remaining = self - need_currency_rate
        for rec in need_currency_rate:
            if rec.l10n_ar_currency_rate:
                rec.computed_currency_rate = rec.l10n_ar_currency_rate
            else:
                rec.computed_currency_rate = rec.currency_id._convert(
                    1.0, rec.company_id.currency_id, rec.company_id,
                    date=rec.date if rec.invoice_date else fields.Date.context_today(rec),
                    round=False)
        remaining.computed_currency_rate = 1.0

    @api.onchange('l10n_ar_currency_rate')
    def _onchange_l10n_ar_reference_currency_rate(self):
        self.l10n_ar_reference_currency_rate = self.l10n_ar_currency_rate


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('move_id.l10n_ar_currency_rate')
    def _compute_currency_rate(self):
        forced = self.filtered(lambda x: x.move_id.l10n_ar_currency_rate)
        for rec in forced:
            rec.currency_rate = 1 / rec.move_id.l10n_ar_currency_rate if (rec.currency_id != rec.move_id.company_currency_id) else 1
        return super(AccountMoveLine, self - forced)._compute_currency_rate()


class AccountChangeCurrency(models.TransientModel):
    # change_type existía en el fork Tecnicanet de account_ux y se sacó por
    # completo en el oficial (que simplificó a un único comportamiento,
    # equivalente al viejo 'value'). Se recrea acá porque change_currency()
    # más abajo lo sigue usando.
    _inherit = 'account.change.currency'

    currency_from = fields.Char(string='Currency From Name', related='currency_from_id.name')
    currency_to = fields.Char(string='Currency To Name', related='currency_to_id.name')
    currency_rate = fields.Float(digits=(16, 6))
    change_type = fields.Selection(
        [('currency', 'Change Only Currency'),
         ('value', 'Update both currency and values')],
        default='currency')
    inverse_currency_rate = fields.Float(string='Inverse Rate',
                                         digits=(16, 6),
                                         required=True,
                                         help="Select a inverse rate to apply on the invoice")
    flag_rate = fields.Boolean(string='Flag Rate')
    flag_inverse_rate = fields.Boolean(string='Flag Inverse Rate')

    @api.onchange('inverse_currency_rate')
    def onchange_inverse_currency_rate(self):
        self.flag_inverse_rate = True
        if self.inverse_currency_rate < 0.0:
            return {'warning': {'title': _('Input Error'),
                                'message': _('The manual inverse rate value must be greater than or equal to 0.0')}}

        if not self.flag_rate:
            self.currency_rate = (1 / self.inverse_currency_rate) if self.inverse_currency_rate > 0.0 else 0.0
        else:
            self.flag_rate = False
            self.flag_inverse_rate = False

    @api.onchange('currency_rate')
    def onchange_currency_rate(self):
        self.flag_rate = True
        if self.currency_rate < 0.0:
            return {'warning': {'title': _('Input Error'),
                                'message': _('The manual rate value must be greater than or equal to 0.0')}}

        if not self.flag_inverse_rate:
            self.inverse_currency_rate = (1 / self.currency_rate) if self.currency_rate > 0.0 else 0.0
        else:
            self.flag_rate = False
            self.flag_inverse_rate = False

    @api.onchange('currency_to_id')
    def onchange_currency(self):
        if not self.currency_to_id:
            self.currency_rate = False
        else:
            self.change_type = 'value'
            currency = self.currency_from_id.with_context(
                )

            currency_rate = currency.with_context(force_rate=self.move_id.l10n_ar_currency_rate)._convert(
                1.0, self.currency_to_id, self.move_id.company_id,
                date=self.move_id.date or
                fields.Date.context_today(self))

            if self.currency_to_id.name == 'ARS' and self.move_id.l10n_ar_currency_rate:
                self.currency_rate = self.move_id.l10n_ar_currency_rate
            elif self.currency_from_id.name == 'ARS' and self.move_id.l10n_ar_currency_rate:
                self.inverse_currency_rate = self.move_id.l10n_ar_currency_rate
            else:
                self.currency_rate = currency_rate

    def change_currency(self):
        self.ensure_one()
        if self.change_type == 'currency':
            self.currency_rate = 1
        message = _("Currency changed from %s to %s with rate %s") % (
            self.move_id.currency_id.name, self.currency_to_id.name,
            self.currency_rate)

        move = self.move_id.with_context(check_move_validity=False)
        for line in move.line_ids:
            # do not round on currency digits, it is rounded automatically
            # on price_unit precision
            line.price_unit = line.price_unit * self.currency_rate
        move.currency_id = self.currency_to_id.id
        move._onchange_currency()

        # This is required to compute to recompute the tax lines again
        if self.currency_rate != 1:
            move._recompute_dynamic_lines(recompute_all_taxes=True)

        if self.currency_from_id.name == 'ARS':
            self.move_id.l10n_ar_currency_rate = self.currency_rate
            self.move_id.l10n_ar_reference_currency_rate = self.currency_rate
        else:
            self.move_id.l10n_ar_currency_rate = self.inverse_currency_rate
            self.move_id.l10n_ar_reference_currency_rate = self.inverse_currency_rate

        self.move_id.message_post(body=message)
        return {'type': 'ir.actions.act_window_close'}



class AccountMoveChangeRate(models.TransientModel):
    # account_ux (oficial) ya define _name = 'account.move.change.rate' con
    # move_id/currency_rate/get_move/_onchange_move/confirm, usando el campo
    # nativo de v18 invoice_currency_rate. Acá lo extendemos: agregamos
    # day_rate y reemplazamos _onchange_move/confirm para usar los campos AR
    # (l10n_ar_currency_rate/computed_currency_rate) en vez del nativo.
    _inherit = 'account.move.change.rate'

    day_rate = fields.Boolean(
        string="Use currency rate of the day",
        help="The currency rate on the invoice date will be used. If the invoice does not have a date, the currency rate will be used at the time of validation.")

    @api.onchange('move_id')
    def _onchange_move(self):
        self.currency_rate = self.move_id.l10n_ar_currency_rate or self.move_id.computed_currency_rate

    def confirm(self):
        move = self.move_id.with_context(check_move_validity=False)
        if self.day_rate:
            currency_rate = move.currency_id._convert(1.0, self.env.company.currency_id, self.move_id.company_id,
                                                      date=self.move_id.date or fields.Date.context_today(self))
        else:
            currency_rate = self.currency_rate

        self.ensure_one()
        message = _("Currency rate changed from %s to %s") % (self.move_id.l10n_ar_currency_rate or self.move_id.computed_currency_rate, self.move_id.computed_currency_rate)


        move.l10n_ar_currency_rate = 0.0 if self.day_rate else currency_rate
        for line in move.line_ids:
            # do not round on currency digits, it is rounded automatically
            # on price_unit precision
            line.balance = line.price_unit * self.currency_rate

        move._onchange_currency()

        # This is required to compute to recompute the tax lines again
        if self.currency_rate != 1:
            move._recompute_dynamic_lines(recompute_all_taxes=True)

        self.move_id.message_post(body=message)
        return {'type': 'ir.actions.act_window_close'}