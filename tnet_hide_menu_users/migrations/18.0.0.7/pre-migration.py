# Pre-migration 18.0.0.7: resolver módulos legacy de localización/checks.
#
# En v15 quedaron instalados módulos ADHOC que ya no existen como addons v18:
# - l10n_ar_account_withholding
# - l10n_latam_check_adhoc
#
# En v18 la funcionalidad base vive en módulos Odoo/OCA diferentes:
# - l10n_ar_withholding
# - l10n_latam_check
#
# Si los legacy quedan en `to upgrade`, Odoo reporta módulos no cargados y
# bloquea dependientes como l10n_ar_ux, l10n_ar_tax, l10n_ar_sale, etc.


def migrate(cr, version):
    if not version:
        return

    legacy_modules = [
        "l10n_ar_account_withholding",
        "l10n_latam_check_adhoc",
    ]
    replacement_modules = [
        "l10n_ar_withholding",
        "l10n_latam_check",
    ]

    # ------------------------------------------------------------------
    # 1. Borrar vistas de módulos legacy y sus hijos.
    # ------------------------------------------------------------------
    cr.execute(
        """
        WITH RECURSIVE view_tree AS (
            SELECT res_id AS id
            FROM ir_model_data
            WHERE model = 'ir.ui.view'
              AND module = ANY(%s)
            UNION ALL
            SELECT child.id
            FROM ir_ui_view child
            JOIN view_tree parent ON child.inherit_id = parent.id
        )
        DELETE FROM ir_ui_view WHERE id IN (SELECT id FROM view_tree)
        """,
        (legacy_modules,),
    )
    print(f"[wall 18.0.0.7] Vistas legacy withholding/check eliminadas: {cr.rowcount}")

    # ------------------------------------------------------------------
    # 2. Borrar external ids de módulos legacy para que Odoo no intente
    #    resolverlos al cerrar el update.
    # ------------------------------------------------------------------
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = ANY(%s)",
        (legacy_modules,),
    )
    print(f"[wall 18.0.0.7] ir_model_data legacy withholding/check eliminados: {cr.rowcount}")

    # ------------------------------------------------------------------
    # 3. Marcar los módulos legacy como uninstalled aunque estuvieran
    #    installed/to upgrade/to remove.
    # ------------------------------------------------------------------
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'uninstalled'
         WHERE name = ANY(%s)
           AND state IN ('installed', 'to upgrade', 'to install', 'to remove')
        """,
        (legacy_modules,),
    )
    print(f"[wall 18.0.0.7] Módulos legacy withholding/check desinstalados: {cr.rowcount}")

    # ------------------------------------------------------------------
    # 4. Preparar reemplazos v18 si existen en ir_module_module.
    #    Si Odoo.sh todavía no los registró, no insertamos manualmente: el
    #    loader debe descubrirlos desde sus manifests core/enterprise.
    # ------------------------------------------------------------------
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = CASE
                WHEN state = 'installed' THEN 'to upgrade'
                WHEN state = 'uninstalled' THEN 'to install'
                ELSE state
           END
         WHERE name = ANY(%s)
           AND state IN ('installed', 'uninstalled')
        """,
        (replacement_modules,),
    )
    print(f"[wall 18.0.0.7] Reemplazos withholding/check preparados: {cr.rowcount}")
