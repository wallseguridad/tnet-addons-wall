# Post-migration 18.0.0.30: migración de costos y precios de productos v15 → v18.
#
# En v15, los campos de costo y precio de los productos estaban en:
#
#   standard_price            → costo contable (product_product, jsonb en Odoo 18)
#   property_currency_id      → moneda del producto (ir.property Many2one)
#   property_profitability_%  → margen de rentabilidad (product_template, jsonb en Odoo 18)
#
# En v18, el módulo product_multi_currency introduce campos nuevos que centralizan
# este concepto. Este script los puebla desde las fuentes v15:
#
#   business_cost             ← standard_price (jsonb de product_product)
#   business_cost_currency_id ← property_currency_id (ir.property)
#   business_markup_rate      ← property_profitability_percentage (jsonb de product_template)
#
# NOTA: estos campos se pre-crean aquí porque product_multi_currency puede
# no haber corrido todavía cuando este script ejecuta (tnet_hide_menu_users
# solo depende de base y corre antes).


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
    # 4. business_markup_rate ← property_profitability_percentage
    #    Campo company_dependent en v15 → jsonb en Odoo 18.
    #    Extraemos el valor para la compañía principal.
    # -------------------------------------------------------------------------
    cr.execute(
        """
        UPDATE product_template
           SET business_markup_rate = (property_profitability_percentage->>%s)::double precision
        """,
        (main_company_id,),
    )
    print(f"[wall 18.0.0.30] business_markup_rate ← property_profitability_percentage: {cr.rowcount} productos actualizados")

    # -------------------------------------------------------------------------
    # 5. business_cost_currency_id ← property_currency_id (ir.property)
    #    En v15, la moneda del producto (precio y costo) estaba en ir.property
    #    como Many2one. No usamos JOIN a ir_model_fields porque Odoo puede
    #    haber limpiado esas entradas durante el upgrade del módulo — en ese
    #    caso el JOIN devuelve 0 filas sin error ni aviso.
    #    En cambio, buscamos por patrón directo: res_id = 'product.template,N'
    #    y value_reference = 'res.currency,N'.
    # -------------------------------------------------------------------------
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables WHERE table_name = 'ir_property'
        )
        """
    )
    if not cr.fetchone()[0]:
        print("[wall 18.0.0.30] ir_property no existe, saltando business_cost_currency_id")
        return

    # Diagnóstico: ¿cuántas filas de moneda hay en ir_property para product.template?
    cr.execute(
        """
        SELECT COUNT(*)
        FROM ir_property
        WHERE type = 'many2one'
          AND value_reference LIKE 'res.currency,%%'
          AND res_id LIKE 'product.template,%%'
        """
    )
    total_currency_rows = cr.fetchone()[0]
    print(f"[wall 18.0.0.30] ir_property filas de moneda para product.template: {total_currency_rows}")

    cr.execute(
        """
        SELECT res_id, value_reference
        FROM ir_property
        WHERE type = 'many2one'
          AND value_reference LIKE 'res.currency,%%'
          AND res_id LIKE 'product.template,%%'
          AND res_id IS NOT NULL AND res_id != ''
          AND value_reference IS NOT NULL
        """
    )
    rows = cr.fetchall()
    migrated = 0
    for res_id_str, value_reference in rows:
        try:
            record_id = int(res_id_str.split(",")[1])
            currency_id = int(value_reference.split(",")[1])
        except (IndexError, ValueError):
            continue
        cr.execute(
            "UPDATE product_template SET business_cost_currency_id = %s WHERE id = %s",
            (currency_id, record_id),
        )
        migrated += cr.rowcount
    print(f"[wall 18.0.0.30] business_cost_currency_id ← property_currency_id: {migrated} productos actualizados")

    print("[wall 18.0.0.30] Migración completada.")
