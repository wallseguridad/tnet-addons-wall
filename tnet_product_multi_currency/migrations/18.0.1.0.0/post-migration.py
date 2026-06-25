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

        # Leer monedas de ir_property por patrón directo — sin JOIN a ir_model_fields.
        # El JOIN falla si Odoo eliminó esas entradas durante el upgrade del shim.
        # property_currency_id y property_cost_currency_id siempre tienen el mismo
        # valor por producto; con DISTINCT evitamos procesar duplicados.
        cr.execute("""
            SELECT DISTINCT res_id, value_reference
            FROM ir_property
            WHERE type = 'many2one'
              AND value_reference LIKE 'res.currency,%%'
              AND res_id LIKE 'product.template,%%'
              AND res_id IS NOT NULL AND res_id != ''
              AND value_reference IS NOT NULL
        """)
        migrated_force = 0
        migrated_cost = 0
        for res_id_str, value_ref in cr.fetchall():
            try:
                template_id = int(res_id_str.split(',')[1])
                currency_id = int(value_ref.split(',')[1])
            except (IndexError, ValueError):
                continue
            if has_force_currency:
                cr.execute(
                    "UPDATE product_template SET force_currency_id = %s WHERE id = %s AND force_currency_id IS NULL",
                    (currency_id, template_id)
                )
                if cr.rowcount:
                    migrated_force += 1
            if has_business_cost_currency:
                cr.execute(
                    "UPDATE product_template SET business_cost_currency_id = %s WHERE id = %s AND business_cost_currency_id IS NULL",
                    (currency_id, template_id)
                )
                if cr.rowcount:
                    migrated_cost += 1
        if has_force_currency:
            print(f"[tnet_product_multi_currency shim] property_currency_id → force_currency_id: {migrated_force} productos")
        if has_business_cost_currency:
            print(f"[tnet_product_multi_currency shim] property_cost_currency_id → business_cost_currency_id: {migrated_cost} productos")

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
