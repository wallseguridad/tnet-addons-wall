# Pre-migration: limpiar vistas inherited huérfanas antes del upgrade v15→v18
#
# Durante el upgrade, Odoo intenta aplicar todas las vistas inherited (inherit_id != NULL)
# almacenadas en la DB. Si una vista padre fue eliminada o renombrada entre versiones,
# la vista hija falla al parsear con "cannot be located in parent view".
#
# Este script elimina las vistas inherited cuyos modelos ya no existen en v18
# o cuyas vistas padre fueron eliminadas, para que el upgrade pueda continuar sin errores.
#
# Ejemplos conocidos en esta migración:
#   - account.change.currency: wizard eliminado en v18, ADHOC lo recrea pero la DB
#     tiene vistas heredadas viejas de v15 que apuntan a la vista padre vieja.


def migrate(cr, version):
    # -------------------------------------------------------------------------
    # 1. Eliminar vistas inherited cuyos modelos ya no existen en v18
    # -------------------------------------------------------------------------
    # Modelos eliminados o renombrados en Odoo v16/v17/v18 que pueden dejar
    # vistas huérfanas en la DB.
    removed_models = [
        'account.change.currency',      # eliminado en v18, recreado por ADHOC
        'account.invoice',              # renombrado a account.move en v13
        'account.invoice.line',         # renombrado a account.move.line en v13
        'sale.advance.payment.inv',     # renombrado en v16
        'account.bank.statement.line',  # restructurado en v15/v16
    ]

    if removed_models:
        placeholders = ','.join(['%s'] * len(removed_models))
        cr.execute(f"""
            DELETE FROM ir_ui_view
            WHERE model IN ({placeholders})
              AND inherit_id IS NOT NULL
        """, removed_models)
        deleted = cr.rowcount
        if deleted:
            print(f"[pre-migration] Eliminadas {deleted} vistas inherited de modelos removidos: {removed_models}")

    # -------------------------------------------------------------------------
    # 2. Eliminar vistas inherited cuyos módulos ya no están instalados
    #    y cuya vista padre fue eliminada (inherit_id apunta a un id inexistente)
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_ui_view child
        WHERE child.inherit_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM ir_ui_view parent
              WHERE parent.id = child.inherit_id
          )
    """)
    deleted_orphan = cr.rowcount
    if deleted_orphan:
        print(f"[pre-migration] Eliminadas {deleted_orphan} vistas inherited con vista padre inexistente (huérfanas)")

    # -------------------------------------------------------------------------
    # 3. Desactivar vistas de módulos que ya no están instalados en v18
    #    (evita que Odoo intente cargarlas durante el upgrade)
    # -------------------------------------------------------------------------
    # Módulos v15 que desaparecieron en v18 (fusionados en otros)
    removed_modules = [
        'account_edi_facturx',
        'account_predictive_bills',
        'account_reports_tax_reminder',
        'fetchmail',
        'fetchmail_gmail',
        'payment_transfer',
        'social_media',
        'website_sale_stock_message',  # custom v15 no migrado aún
        'website_price_tax_custom',    # custom v15 no migrado aún
        'website_product_custom',      # custom v15 no migrado aún
    ]

    if removed_modules:
        cr.execute("""
            UPDATE ir_ui_view SET active = FALSE
            WHERE active = TRUE
              AND id IN (
                  SELECT res_id FROM ir_model_data
                  WHERE model = 'ir.ui.view'
                    AND module = ANY(%s)
              )
        """, (removed_modules,))
        deactivated = cr.rowcount
        if deactivated:
            print(f"[pre-migration] Desactivadas {deactivated} vistas de módulos eliminados en v18")

    print("[pre-migration] Limpieza de vistas completada.")
