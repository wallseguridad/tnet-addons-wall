# Post-migration 18.0.0.20: poblar business_cost / business_cost_currency_id /
# business_markup_rate desde v15.
#
# Estos campos son nuevos en v18 (product_multi_currency). Sus fuentes en v15:
#
#   business_cost             ← standard_price (product_product, jsonb en Odoo 18)
#   business_cost_currency_id ← property_currency_id (ir.property Many2one)
#   business_markup_rate      ← property_profitability_percentage (jsonb en Odoo 18)
#
# force_currency_id y otros campos de product_currency aún no existen en este
# punto del upgrade — hay que leer property_currency_id directo de ir_property.


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

    # Compañía principal para campos jsonb
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
    print(f"[wall 18.0.0.20] business_cost ← standard_price (empresa {main_company_id}): {cr.rowcount} productos")

    # business_markup_rate ← property_profitability_percentage (jsonb en Odoo 18)
    cr.execute(
        """
        UPDATE product_template
           SET business_markup_rate = (property_profitability_percentage->>%s)::double precision
        """,
        (main_company_id,),
    )
    print(f"[wall 18.0.0.20] business_markup_rate ← property_profitability_percentage: {cr.rowcount} productos")

    # business_cost_currency_id ← property_currency_id (desde ir_property)
    # force_currency_id no existe todavía en este punto del upgrade
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables WHERE table_name = 'ir_property'
        )
        """
    )
    if cr.fetchone()[0]:
        cr.execute(
            """
            SELECT p.res_id, p.value_reference
            FROM ir_property p
            JOIN ir_model_fields f ON f.id = p.fields_id
            WHERE f.name = 'property_currency_id'
              AND p.res_id IS NOT NULL AND p.res_id != ''
              AND p.type = 'many2one'
              AND p.value_reference IS NOT NULL
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
        print(f"[wall 18.0.0.20] business_cost_currency_id ← property_currency_id: {migrated} productos")

    print("[wall 18.0.0.20] Migración completada.")
