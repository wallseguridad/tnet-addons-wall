# Pre-migration 18.0.0.15: limpiar group_ids legacy en menús de pagos.
#
# En v15, tnet_hide_menu_users restringía los menús de pagos al grupo custom
# "See Payments Menu" (sin XMLID). En v18 el módulo usa ir.rule +
# restrict_user_ids en lugar de grupos. Los menús todavía tenían ese group_id
# legacy, haciendo que cualquier usuario sin el grupo no los vea.


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        DELETE FROM ir_ui_menu_group_rel
        WHERE menu_id IN (
            SELECT imd.res_id
            FROM ir_model_data imd
            WHERE imd.module = 'account'
              AND imd.name IN (
                'menu_action_account_payments_receivable',
                'menu_action_account_payments_payable'
              )
              AND imd.model = 'ir.ui.menu'
        )
    """)
    print(f"[wall 18.0.0.15] group_ids legacy removidos de menús de pagos: {cr.rowcount} filas")
