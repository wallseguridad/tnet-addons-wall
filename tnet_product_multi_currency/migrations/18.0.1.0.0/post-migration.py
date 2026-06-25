# Migración shim: tnet_product_multi_currency v15 → product_multi_currency v18
#
# En v15 los campos de moneda eran company_dependent almacenados en ir.property:
#   product.template.property_currency_id   → moneda del precio de lista
#   product.template.property_cost_currency_id → moneda del costo
#
# En v18:
#   property_currency_id      → force_currency_id  (adhoc/product_currency)
#   property_cost_currency_id → business_cost_currency_id (product_multi_currency)
#
# Este script corre porque tnet_product_multi_currency existe en disco (shim)
# y Odoo lo upgradea desde la versión v15 — a diferencia del módulo renombrado
# product_multi_currency que Odoo instalaría fresh (sin correr migrations/).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    # -------------------------------------------------------------------------
    # 1. Migrar property_currency_id → force_currency_id
    # -------------------------------------------------------------------------
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables WHERE table_name = 'ir_property'
        )
    """)
    if not cr.fetchone()[0]:
        print("[tnet_product_multi_currency shim] ir_property no existe, saltando migración v15.")
    else:
        cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'product_template' AND column_name = 'force_currency_id'
            )
        """)
        has_force_currency = cr.fetchone()[0]

        cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'product_template' AND column_name = 'business_cost_currency_id'
            )
        """)
        has_business_cost_currency = cr.fetchone()[0]

        # Migrar monedas desde columnas jsonb (Odoo eliminó ir_property antes de las post-migrations).
        # property_currency_id y property_cost_currency_id ya están como jsonb {"company_id": currency_id}.
        cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
        row = cr.fetchone()
        main_company_id = str(row[0]) if row else "1"

        if has_force_currency:
            cr.execute("""
                UPDATE product_template
                   SET force_currency_id = (property_currency_id->>%s)::integer
                 WHERE property_currency_id IS NOT NULL
                   AND (property_currency_id->>%s) IS NOT NULL
                   AND force_currency_id IS NULL
            """, (main_company_id, main_company_id))
            print(f"[tnet_product_multi_currency shim] property_currency_id → force_currency_id: {cr.rowcount} productos")

        if has_business_cost_currency:
            cr.execute("""
                UPDATE product_template
                   SET business_cost_currency_id = (property_cost_currency_id->>%s)::integer
                 WHERE property_cost_currency_id IS NOT NULL
                   AND (property_cost_currency_id->>%s) IS NOT NULL
                   AND business_cost_currency_id IS NULL
            """, (main_company_id, main_company_id))
            print(f"[tnet_product_multi_currency shim] property_cost_currency_id → business_cost_currency_id: {cr.rowcount} productos")

    # -------------------------------------------------------------------------
    # 2. Fallback: setear USD en productos sin moneda asignada
    # -------------------------------------------------------------------------
    cr.execute("SELECT id FROM res_currency WHERE name = 'USD' AND active = TRUE LIMIT 1")
    row = cr.fetchone()
    if row:
        usd_id = row[0]
        cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'product_template' AND column_name = 'force_currency_id'
            )
        """)
        if cr.fetchone()[0]:
            cr.execute("""
                UPDATE product_template SET force_currency_id = %s WHERE force_currency_id IS NULL
            """, (usd_id,))
            print(f"[tnet_product_multi_currency shim] force_currency_id = USD (fallback): {cr.rowcount} productos")

    # -------------------------------------------------------------------------
    # 3. Recomputar currency_id (campo compute store=True) via ORM
    # -------------------------------------------------------------------------
    env = api.Environment(cr, SUPERUSER_ID, {})
    templates = env['product.template'].with_context(active_test=False).search([
        ('force_currency_id', '!=', False)
    ])
    if templates:
        templates._compute_currency_id()
        print(f"[tnet_product_multi_currency shim] currency_id recomputado: {len(templates)} productos")

    print("[tnet_product_multi_currency shim] Migración completada.")
