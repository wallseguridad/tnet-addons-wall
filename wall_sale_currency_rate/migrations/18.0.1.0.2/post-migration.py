# -*- coding: utf-8 -*-
# Poblar l10n_ar_price_unit_usd para líneas de órdenes confirmadas que no lo tienen.
# Estas son órdenes migradas de v15 donde el campo no existía.


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID, fields

    env = api.Environment(cr, SUPERUSER_ID, {})

    usd = env.ref("base.USD", raise_if_not_found=False)
    if not usd:
        print("[post-migration wall_sale_currency_rate] USD no encontrado, saltando.")
        return

    lines = env["sale.order.line"].search([
        ("order_id.state", "in", ["sale", "done"]),
        ("l10n_ar_price_unit_usd", "=", 0.0),
        ("price_unit", "!=", 0.0),
        ("display_type", "=", False),
    ])

    count = 0
    for line in lines:
        order = line.order_id
        currency_from = (
            order.pricelist_id.currency_id
            or order.currency_id
            or order.company_id.currency_id
        )
        date = order.date_order.date() if order.date_order else fields.Date.today()

        if currency_from == usd:
            price_usd = line.price_unit
        else:
            price_usd = currency_from._convert(
                line.price_unit, usd, order.company_id, date
            )

        cr.execute(
            "UPDATE sale_order_line SET l10n_ar_price_unit_usd = %s WHERE id = %s",
            (price_usd, line.id),
        )
        count += 1

    print(f"[post-migration wall_sale_currency_rate] l10n_ar_price_unit_usd poblado en {count} líneas.")
