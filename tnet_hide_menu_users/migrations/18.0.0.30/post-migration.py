# Post-migration 18.0.0.30: migración de costos y precios de productos v15 → v18.
#
# HALLAZGO CLAVE: Odoo elimina ir_property completamente ANTES de ejecutar las
# post-migrations. Los datos v15 de campos company_dependent ya están migrados
# a columnas jsonb {"company_id": value} cuando este script corre.
#
# Fuentes en v18 (todas como jsonb en product_template):
#   business_cost             ← standard_price         (en product_product)
#   business_cost_currency_id ← property_cost_currency_id  (integer)
#   business_markup_rate      ← property_profitability_percentage (float)


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

    # -------------------------------------------------------------------------
    # 4. business_cost_currency_id ← property_cost_currency_id (jsonb)
    #    Odoo migra automáticamente ir_property → columna jsonb durante el
    #    upgrade. Misma extracción que standard_price.
    # -------------------------------------------------------------------------
    cr.execute(
        """
        UPDATE product_template
           SET business_cost_currency_id = (property_cost_currency_id->>%s)::integer
         WHERE property_cost_currency_id IS NOT NULL
           AND (property_cost_currency_id->>%s) IS NOT NULL
        """,
        (main_company_id, main_company_id),
    )
    print(f"[wall 18.0.0.30] business_cost_currency_id ← property_cost_currency_id: {cr.rowcount} productos actualizados")

    # -------------------------------------------------------------------------
    # 5. business_markup_rate ← property_profitability_percentage (jsonb)
    # -------------------------------------------------------------------------
    cr.execute(
        """
        UPDATE product_template
           SET business_markup_rate = (property_profitability_percentage->>%s)::double precision
         WHERE property_profitability_percentage IS NOT NULL
           AND (property_profitability_percentage->>%s) IS NOT NULL
        """,
        (main_company_id, main_company_id),
    )
    print(f"[wall 18.0.0.30] business_markup_rate ← property_profitability_percentage: {cr.rowcount} productos actualizados")

    print("[wall 18.0.0.30] Migración completada.")
