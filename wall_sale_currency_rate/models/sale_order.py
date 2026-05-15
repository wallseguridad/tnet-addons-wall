# -*- coding: utf-8 -*-
from lxml import etree

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != 'form' or not res.get('arch'):
            return res

        # sale_order_general_discount injecta dinámicamente:
        #   {'default_discount': general_discount, ...}
        # En Odoo 18 OWL puede evaluar el contexto antes de que el campo esté
        # disponible en el eval context, provocando NameError. Dejamos el valor
        # seguro en 0.0; el módulo OCA igualmente recalcula el descuento de la
        # línea desde order_id.general_discount en sale.order.line.
        arch = etree.XML(res['arch'])
        changed = False
        for order_line in arch.xpath("//field[@name='order_line'][@context]"):
            context = order_line.attrib.get('context') or ''
            sanitized = context.replace(
                "'default_discount': general_discount, ",
                "'default_discount': 0.0, ",
            ).replace(
                '"default_discount": general_discount, ',
                '"default_discount": 0.0, ',
            )
            if sanitized != context:
                order_line.attrib['context'] = sanitized
                changed = True
        if changed:
            res['arch'] = etree.tostring(arch, encoding='unicode')
        return res

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
