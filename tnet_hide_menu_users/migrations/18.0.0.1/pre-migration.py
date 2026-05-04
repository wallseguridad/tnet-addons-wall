# Pre-migration 18.0.0.1: limpiar residuos de account_payment_group en instancias existentes.
#
# account_payment_group (ADHOC v15) definía el modelo account.payment.group.
# En v18 fue absorbido por account_payment_pro (solo usa account.payment).
# El módulo no tiene código en disco en v18. Sus registros DB (menús, acciones,
# vistas, ir.model) quedan huérfanos y provocan el error 404 al abrir pagos.


def migrate(cr, version):
    if not version:
        return

    # -------------------------------------------------------------------------
    # 1. Marcar account_payment_group como uninstalled
    #    La migración 18.0.0.0 lo dejó en 'to upgrade' por error.
    # -------------------------------------------------------------------------
    cr.execute("""
        UPDATE ir_module_module
        SET state = 'uninstalled'
        WHERE name = 'account_payment_group'
          AND state IN ('installed', 'to upgrade', 'to remove')
    """)
    print(f"[wall 18.0.0.1] account_payment_group marcado uninstalled: {cr.rowcount}")

    # -------------------------------------------------------------------------
    # 2. Eliminar menús que apuntan a acciones de account.payment.group
    #    ir_ui_menu.action almacena 'ir.actions.act_window,{id}'
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_ui_menu
        WHERE action IN (
            SELECT 'ir.actions.act_window,' || id::text
            FROM ir_act_window
            WHERE res_model = 'account.payment.group'
        )
    """)
    print(f"[wall 18.0.0.1] Menús de account.payment.group eliminados: {cr.rowcount}")

    # -------------------------------------------------------------------------
    # 3. Eliminar acciones de ventana que abren account.payment.group
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_act_window
        WHERE res_model = 'account.payment.group'
    """)
    print(f"[wall 18.0.0.1] ir.actions.act_window de account.payment.group: {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 4. Eliminar vistas (inherited y base) del modelo account.payment.group
    #    Usamos CTE recursivo para borrar también las vistas hijo.
    # -------------------------------------------------------------------------
    cr.execute("""
        WITH RECURSIVE view_tree AS (
            SELECT id FROM ir_ui_view
            WHERE model = 'account.payment.group'
            UNION ALL
            SELECT child.id FROM ir_ui_view child
            JOIN view_tree parent ON child.inherit_id = parent.id
        )
        DELETE FROM ir_ui_view WHERE id IN (SELECT id FROM view_tree)
    """)
    print(f"[wall 18.0.0.1] Vistas de account.payment.group eliminadas (con hijos): {cr.rowcount}")

    # -------------------------------------------------------------------------
    # 5. Limpiar ir.model.data del módulo account_payment_group
    #    Deja los campos/modelos huérfanos sin external ID — Odoo los ignorará.
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'account_payment_group'
    """)
    print(f"[wall 18.0.0.1] ir.model.data de account_payment_group: {cr.rowcount} eliminados")

    print("[wall 18.0.0.1] Limpieza account_payment_group completada.")
