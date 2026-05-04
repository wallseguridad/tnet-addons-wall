# Pre-migration 18.0.0.3: limpiar vista huérfana con invoice_status_posted.
#
# Elemento QWeb <t name="invoice_status_posted"> fue removido/renombrado en v18.
# Vistas inherited de v15 que lo referencian vía XPath fallan la validación en v18.


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE inherit_id IS NOT NULL
          AND arch_db::text LIKE '%invoice_status_posted%'
    """)
    print(f"[wall 18.0.0.3] Vistas con invoice_status_posted: {cr.rowcount} eliminadas")
