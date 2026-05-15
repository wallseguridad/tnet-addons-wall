# Pre-migration 18.0.0.11: limpiar nuevamente vistas heredadas legacy
# que apuntan al template/QWeb `invoice_status_posted`.
#
# Al actualizar todos los módulos desde la UI puede reaparecer el error:
#   El elemento "<xpath expr=\"//t[@name='invoice_status_posted']/span[1]\">"
#   no se puede localizar en la vista principal
#
# La limpieza 18.0.0.3 ya cubría el caso inicial, pero no vuelve a ejecutarse
# cuando la versión instalada del módulo ya avanzó. Este bump fuerza una nueva
# pasada y elimina también hijos/ir_model_data para evitar residuos.


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        WITH RECURSIVE target AS (
            SELECT id
              FROM ir_ui_view
             WHERE inherit_id IS NOT NULL
               AND arch_db::text LIKE '%invoice_status_posted%'
            UNION ALL
            SELECT child.id
              FROM ir_ui_view child
              JOIN target parent ON child.inherit_id = parent.id
        ), deleted_imd AS (
            DELETE FROM ir_model_data
             WHERE model = 'ir.ui.view'
               AND res_id IN (SELECT id FROM target)
            RETURNING 1
        )
        DELETE FROM ir_ui_view
         WHERE id IN (SELECT id FROM target)
        """
    )
    print(f"[wall 18.0.0.11] Vistas legacy invoice_status_posted eliminadas: {cr.rowcount}")
