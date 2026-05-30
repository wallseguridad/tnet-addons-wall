# Limpiar vistas v15 de tnet_product_multi_currency antes del upgrade.
# En v15 este módulo definía lst_price en sale.order.line. En v18 ese campo
# no existe, por lo que OWL falla con "field is undefined" al renderizar
# la vista de pedidos de venta.


def migrate(cr, version):
    # Borrar todas las vistas del módulo con CTE recursivo para cubrir hijos
    cr.execute("""
        WITH RECURSIVE view_tree AS (
            SELECT res_id AS id
            FROM ir_model_data
            WHERE model = 'ir.ui.view'
              AND module = 'tnet_product_multi_currency'
            UNION ALL
            SELECT child.id
            FROM ir_ui_view child
            JOIN view_tree parent ON child.inherit_id = parent.id
        )
        DELETE FROM ir_ui_view WHERE id IN (SELECT id FROM view_tree)
    """)
    print(f"[tnet_product_multi_currency shim] Vistas v15 eliminadas: {cr.rowcount}")

    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'tnet_product_multi_currency' AND model = 'ir.ui.view'"
    )
    print(f"[tnet_product_multi_currency shim] ir_model_data de vistas eliminados: {cr.rowcount}")
