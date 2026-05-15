# Pre-migration 18.0.0.8: desactivar vista kanban incompatible del dashboard contable.
#
# account_multicompany_ux (repo externo ADHOC) hereda el kanban dashboard de
# account.journal y cambia dentro del template un <field name="name"> por
# <field name="display_name">. En Odoo 18 el KanbanArchParser espera que todo
# <field> usado dentro del template exista en la lista de fields de la vista;
# al no estar declarado display_name, el frontend falla al entrar a
# Contabilidad con:
#   TypeError: Cannot read properties of undefined (reading 'type')
#
# Como no tocamos repos externos durante esta migración, desactivamos solamente
# esa vista heredada en DB. La funcionalidad perdida es cosmética: mostrar el
# nombre calculado multi-compañía en la tarjeta de diarios.


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        WITH target AS (
            SELECT res_id AS id
              FROM ir_model_data
             WHERE module = 'account_multicompany_ux'
               AND name = 'account_journal_dashboard_kanban_view'
               AND model = 'ir.ui.view'
        )
        UPDATE ir_ui_view
           SET active = FALSE
         WHERE id IN (SELECT id FROM target)
           AND active IS DISTINCT FROM FALSE
        """
    )
    print(
        "[wall 18.0.0.8] Vista kanban dashboard incompatible "
        f"account_multicompany_ux desactivada: {cr.rowcount}"
    )
