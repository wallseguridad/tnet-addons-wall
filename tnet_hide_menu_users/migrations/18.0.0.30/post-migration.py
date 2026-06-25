# Post-migration 18.0.0.30: migración de costos y precios de productos v15 → v18.
#
# Responsabilidades de este script (corre primero — solo depende de base):
#   business_cost ← standard_price (Odoo ya migró ir_property → jsonb antes de las post-migrations)
#
# Responsabilidades delegadas a los shims (corren después, con los campos ya definidos):
#   business_cost_currency_id ← tnet_product_multi_currency shim (property_cost_currency_id)
#   business_markup_rate      ← tnet_product_profitability (property_profitability_percentage)
#
# NOTA: las columnas se pre-crean aquí porque product_multi_currency puede
# no haber corrido todavía su ORM update cuando este script ejecuta.


def migrate(cr, version):
    if not version:
        return

    # -------------------------------------------------------------------------
    # 1. Pre-crear columnas
    #    product_multi_currency las crea en su ORM update, pero ese módulo
    #    puede correr DESPUÉS de este script. ADD COLUMN IF NOT EXISTS es no-op
    #    si ya existen.
    # -------------------------------------------------------------------------
    cr.execute(
        """
        ALTER TABLE product_template
            ADD COLUMN IF NOT EXISTS business_cost             DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS business_cost_currency_id INTEGER,
            ADD COLUMN IF NOT EXISTS business_markup_rate      DOUBLE PRECISION
        """
    )
    print("[wall 18.0.0.30] Columnas business_cost* aseguradas")

    # -------------------------------------------------------------------------
    # 2. Compañía principal (para extraer valores de campos jsonb)
    #    En Odoo 18, los campos company_dependent se guardan como
    #    jsonb {"company_id": value}. Usamos el id de la compañía raíz.
    # -------------------------------------------------------------------------
    cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
    row = cr.fetchone()
    main_company_id = str(row[0]) if row else "1"
    print(f"[wall 18.0.0.30] Compañía principal: {main_company_id}")

    # -------------------------------------------------------------------------
    # 3. business_cost ← standard_price
    #    standard_price vive en product_product (no en product_template).
    #    En Odoo 18 es company_dependent → jsonb {"1": 150.0}.
    #    Tomamos el primer variant ordenado por id.
    # -------------------------------------------------------------------------
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
    print(f"[wall 18.0.0.30] business_cost ← standard_price: {cr.rowcount} productos actualizados")
    print("[wall 18.0.0.30] Migración completada.")
