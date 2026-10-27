# -*- coding: utf-8 -*-
# l10n_ar_price_unit_usd en compras pasa a ser neto de descuento.
# Para las líneas ya guardadas aplicamos el descuento sobre el valor
# almacenado (sin reconvertir), así se conserva el tipo de cambio
# con el que se calculó originalmente.


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE purchase_order_line
           SET l10n_ar_price_unit_usd = l10n_ar_price_unit_usd * (1 - discount / 100.0)
         WHERE COALESCE(discount, 0) != 0
           AND COALESCE(l10n_ar_price_unit_usd, 0) != 0
    """)
