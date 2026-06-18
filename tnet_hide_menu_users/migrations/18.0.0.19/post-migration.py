# Post-migration 18.0.0.19: poblar business_cost desde replenishment_base_cost.
#
# business_cost es un campo nuevo en v18 (product_multi_currency). No existía
# en v15. El equivalente conceptual en v15 era replenishment_base_cost (el costo
# base del producto en su moneda).
#
# Una vez poblado, _sync_standard_price_with_business_cost y
# _sync_list_price_with_business_price (product_multi_currency) se encargan
# de propagar el valor a standard_price y list_price.


def migrate(cr, version):
    if not version:
        return

    # Poblar business_cost desde replenishment_base_cost donde esté vacío
    cr.execute(
        """
        UPDATE product_template
           SET business_cost = replenishment_base_cost
         WHERE (business_cost IS NULL OR business_cost = 0)
           AND replenishment_base_cost IS NOT NULL
           AND replenishment_base_cost != 0
        """
    )
    cost_count = cr.rowcount
    print(f"[wall 18.0.0.19] business_cost ← replenishment_base_cost: {cost_count} productos")

    # Poblar business_cost_currency_id desde replenishment_base_cost_currency_id
    # donde business_cost fue recién populado y la moneda está vacía
    cr.execute(
        """
        UPDATE product_template
           SET business_cost_currency_id = replenishment_base_cost_currency_id
         WHERE (business_cost_currency_id IS NULL)
           AND replenishment_base_cost_currency_id IS NOT NULL
           AND replenishment_base_cost != 0
        """
    )
    currency_count = cr.rowcount
    print(f"[wall 18.0.0.19] business_cost_currency_id ← replenishment_base_cost_currency_id: {currency_count} productos")

    print(f"[wall 18.0.0.19] Migración completada.")
