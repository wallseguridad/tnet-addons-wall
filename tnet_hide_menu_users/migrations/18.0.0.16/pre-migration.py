# Pre-migration 18.0.0.16: forzar instalación de módulos post-upgrade.
#
# wall_sale_compat: patch get_view para sale_order_general_discount (Odoo 18).
# l10n_ar_payment_bundle: módulo de pagos agrupados AR.
#
# Marcarlos como 'to install' aquí garantiza que Odoo los instale en el mismo
# run de upgrade, tanto en Odoo.sh como localmente. El módulo debe estar en el
# addons path para que ya exista en ir_module_module al momento de correr esto.


MODULES_TO_INSTALL = [
    'wall_sale_compat',
    'l10n_ar_payment_bundle',
]


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to install'
        WHERE name = ANY(%s)
          AND state = 'uninstalled'
    """, (MODULES_TO_INSTALL,))
    print(f"[wall 18.0.0.16] módulos marcados como 'to install': {cr.rowcount} ({', '.join(MODULES_TO_INSTALL)})")
