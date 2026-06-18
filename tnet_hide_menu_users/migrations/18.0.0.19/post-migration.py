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

    # business_cost ← standard_price del primer variant activo
    # standard_price ya fue migrado por Odoo desde ir.property → product_product
    cr.execute(
        """
        UPDATE product_template t
           SET business_cost = (
               SELECT pp.standard_price
               FROM product_product pp
               WHERE pp.product_tmpl_id = t.id
               ORDER BY pp.id
               LIMIT 1
           )
         WHERE (t.business_cost IS NULL OR t.business_cost = 0)
           AND EXISTS (
               SELECT 1 FROM product_product pp
               WHERE pp.product_tmpl_id = t.id
                 AND pp.standard_price IS NOT NULL
                 AND pp.standard_price != 0
           )
        """
    )
    print(f"[wall 18.0.0.19] business_cost ← standard_price: {cr.rowcount} productos")

    # business_markup_rate ← property_profitability_percentage
    # (ya migrado a columna directa por tnet_product_profitability o aún en tabla)
    cr.execute(
        """
        UPDATE product_template
           SET business_markup_rate = property_profitability_percentage
         WHERE (business_markup_rate IS NULL OR business_markup_rate = 0)
           AND property_profitability_percentage IS NOT NULL
           AND property_profitability_percentage != 0
        """
    )
    print(f"[wall 18.0.0.19] business_markup_rate ← property_profitability_percentage: {cr.rowcount} productos")

    print("[wall 18.0.0.19] Migración completada.")
