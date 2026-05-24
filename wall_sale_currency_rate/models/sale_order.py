# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        if 'l10n_ar_currency_rate_ids' not in vals:
            return super().write(vals)

        # Separar pedidos confirmados (state='sale') de los demás.
        # El módulo padre (manual_currency_rate_sale) bloquea la escritura de
        # l10n_ar_currency_rate_ids para cualquier estado fuera de draft/sent.
        # Para wall, permitimos editarlo también en state='sale'.
        sale_orders = self.filtered(lambda o: o.state == 'sale')
        other_orders = self - sale_orders

        result = True

        # Pedidos en otros estados: flujo normal del padre
        if other_orders:
            result = super(SaleOrder, other_orders).write(vals)

        if sale_orders:
            clean_cmds = sale_orders._sanitize_currency_rate_commands(
                vals['l10n_ar_currency_rate_ids']
            )

            # Escribir campos que NO son las tasas vía super() normal (sin restricción)
            other_vals = {k: v for k, v in vals.items() if k != 'l10n_ar_currency_rate_ids'}
            if other_vals:
                result = super(SaleOrder, sale_orders).write(other_vals) and result

            # Escribir las tasas directamente en su modelo para evitar la restricción
            # del write() del padre que bloquea en state='sale'
            Rate = self.env['l10n.ar.currency.rate']
            for order in sale_orders:
                for cmd in clean_cmds:
                    if not isinstance(cmd, (list, tuple)) or len(cmd) < 2:
                        continue
                    op = cmd[0]
                    if op == 0 and len(cmd) >= 3:   # create
                        Rate.create({**cmd[2], 'sale_order_id': order.id})
                    elif op == 1 and len(cmd) >= 3:  # update
                        Rate.browse(cmd[1]).write(cmd[2])
                    elif op == 2:                    # delete
                        Rate.browse(cmd[1]).unlink()

            # Reaplicar precios con las nuevas tasas
            for order in sale_orders:
                ctx = order._get_currency_manual_rates_context()
                order.with_context(**ctx)._l10n_ar_apply_sale_state_prices()

        return result

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id_wall(self):
        """Disparar repricing cuando cambia la lista de precios en state='sale'."""
        for order in self:
            if order.state == 'sale' and order.pricelist_id:
                ctx = order._get_currency_manual_rates_context()
                order.with_context(**ctx)._l10n_ar_apply_sale_state_prices()
                # Evitar que aparezca el banner "Actualizar precios" en órdenes
                # confirmadas: el repricing por TC ya se aplicó automáticamente.
                order.show_update_pricelist = False
