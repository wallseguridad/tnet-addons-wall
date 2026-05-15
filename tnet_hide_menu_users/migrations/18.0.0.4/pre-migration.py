# Pre-migration 18.0.0.4: restaurar acciones de pago nativas de Odoo.
#
# La migración 18.0.0.1 borró todos los ir_act_window con
# res_model = 'account.payment.group'. Eso incluye acciones que en v15
# account_payment_group había sobreescrito: account.action_account_payments
# y account.action_account_payments_payable (originalmente de account).
#
# Fix: eliminar los ir_model_data fantasma (res_id apunta a un act_window
# que ya no existe) y limpiar los ir_ui_menu con acción inválida.
#
# NOTA: el force-upgrade de `account` fue removido — la migración 18.0.0.12
# recrea las acciones de pago directamente via SQL sin depender del XML de
# account. Forzar el upgrade de account hace que su _process_end() elimine
# account.email_template_edi_invoice del ir_model_data si la versión ADHOC
# no lo redefine, rompiendo account_ux/data/mail_template_data.xml.


def migrate(cr, version):
    if not version:
        return

    # -------------------------------------------------------------------------
    # 1. Limpiar ir_model_data con res_id apuntando a act_window inexistente
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'ir.actions.act_window'
          AND res_id NOT IN (SELECT id FROM ir_act_window)
    """)
    print(f"[wall 18.0.0.4] ir_model_data con act_window inexistente: {cr.rowcount} eliminados")

    # -------------------------------------------------------------------------
    # 2. Limpiar ir_ui_menu con acción apuntando a act_window inexistente
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

    print("[wall 18.0.0.4] Restauración de acciones de pago completada.")
