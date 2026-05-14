# Pre-migration 18.0.0.6: preparar columna de sale_order_general_discount.
#
# Odoo.sh ejecuta ir_autovacuum durante el upgrade. Si el registry ya conoce
# product.product.bypass_general_discount pero la columna todavía no existe,
# stock.warehouse.orderpoint puede leer productos y fallar antes de que el
# módulo OCA sale_order_general_discount termine su actualización.


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        ALTER TABLE product_product
        ADD COLUMN IF NOT EXISTS bypass_general_discount BOOLEAN
    """)
    print("[wall 18.0.0.6] product_product.bypass_general_discount asegurada")
