# Pre-migration 18.0.0.4: restaurar acciones de pago nativas de Odoo.
#
# La migración 18.0.0.1 borró todos los ir_act_window con
# res_model = 'account.payment.group'. Eso incluye acciones que en v15
# account_payment_group había sobreescrito: account.action_account_payments
# y account.action_account_payments_payable (originalmente de account).
#
# Consecuencia: los menús Contabilidad > Clientes/Proveedores > Pagos
# quedaron apuntando a registros ir_act_window inexistentes → desaparecen
# del menú o dan error al abrirse.
#
# Fix: eliminar los ir_model_data fantasma (res_id apunta a un act_window
# que ya no existe) y limpiar los ir_ui_menu con acción inválida.
# En el próximo upgrade del módulo `account`, Odoo recrea esas acciones
# apuntando a account.payment (comportamiento correcto de v18).


def migrate(cr, version):
    if not version:
        return

    # -------------------------------------------------------------------------
    # 1. Limpiar ir_model_data con res_id apuntando a act_window inexistente
    #    Cuando Odoo actualiza `account`, recrea estas entradas apuntando
    #    a account.payment en lugar de account.payment.group.
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'ir.actions.act_window'
          AND res_id NOT IN (SELECT id FROM ir_act_window)
    """)
    print(f"[wall 18.0.0.4] ir_model_data con act_window inexistente: {cr.rowcount} eliminados")

    # -------------------------------------------------------------------------
    # 2. Limpiar ir_ui_menu con acción apuntando a act_window inexistente
    #    Odoo recrea los menús nativos al actualizar el módulo account.
    # -------------------------------------------------------------------------
    cr.execute(r"""
        UPDATE ir_ui_menu
        SET action = NULL
        WHERE action ~ '^ir\.actions\.act_window,[0-9]+$'
          AND CAST(split_part(action, ',', 2) AS INTEGER) NOT IN (
              SELECT id FROM ir_act_window
          )
    """)
    print(f"[wall 18.0.0.4] ir_ui_menu con acción de pago inválida: {cr.rowcount} limpiados")

    # -------------------------------------------------------------------------
    # 3. Forzar upgrade del módulo account para que recree las acciones
    #    nativas (action_account_payments, action_account_payments_payable).
    # -------------------------------------------------------------------------
    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to upgrade'
        WHERE name = 'account'
          AND state = 'installed'
    """)
    print(f"[wall 18.0.0.4] Módulo account marcado para upgrade: {cr.rowcount}")

    print("[wall 18.0.0.4] Restauración de acciones de pago completada.")
