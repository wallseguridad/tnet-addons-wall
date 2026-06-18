# Post-migration 18.0.0.19: poblar business_cost / business_markup_rate desde v15.
#
# business_cost y business_markup_rate son campos nuevos en v18 (product_multi_currency).
# No existían en v15. Sus fuentes en v15 son:
#
#   business_cost          ← standard_price  (product_product, ya migrado por Odoo)
#   business_cost_currency_id ← business_cost_currency_id (ya migrado desde property_cost_currency_id)
#   business_markup_rate   ← property_profitability_percentage (product_template)


def migrate(cr, version):
    if not version:
        return

    # Pre-crear columnas en caso de que product_multi_currency aún no las haya creado
    cr.execute(
        """
        ALTER TABLE product_template
            ADD COLUMN IF NOT EXISTS business_cost        DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS business_cost_currency_id INTEGER,
            ADD COLUMN IF NOT EXISTS business_markup_rate DOUBLE PRECISION
        """
    )

    # standard_price en Odoo 18 es company_dependent → jsonb {"company_id": value}
    # Extraemos el valor de la compañía principal (la de menor id)
    cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
    row = cr.fetchone()
    main_company_id = str(row[0]) if row else "1"

    # business_cost ← standard_price del primer variant (jsonb → float)
    cr.execute(
        """
        UPDATE product_template t
           SET business_cost = (
               SELECT (pp.standard_price->>%s)::double precision
               FROM product_product pp
               WHERE pp.product_tmpl_id = t.id
               ORDER BY pp.id
               LIMIT 1
           )
        """,
        (main_company_id,),
    )
    print(f"[wall 18.0.0.19] business_cost ← standard_price (empresa {main_company_id}): {cr.rowcount} productos")

    # business_markup_rate ← property_profitability_percentage (jsonb en Odoo 18)
    cr.execute(
        """
        UPDATE product_template
           SET business_markup_rate = (property_profitability_percentage->>%s)::double precision
        """,
        (main_company_id,),
    )
    print(f"[wall 18.0.0.19] business_markup_rate ← property_profitability_percentage: {cr.rowcount} productos")

    # business_cost_currency_id: la mayoría de productos en v15 usaban la moneda
    # de la empresa por defecto (sin registro en ir.property). Setear fallback donde NULL.
    cr.execute(
        """
        UPDATE product_template
           SET business_cost_currency_id = (
               SELECT currency_id FROM res_company ORDER BY id LIMIT 1
           )
         WHERE business_cost_currency_id IS NULL
        """
    )
    print(f"[wall 18.0.0.19] business_cost_currency_id ← moneda empresa (fallback): {cr.rowcount} productos")

    print("[wall 18.0.0.19] Migración completada.")
