# Pre-migration 18.0.0.31: limpieza de residuos de la arquitectura MCR nueva
# en la branch 18.0-parity.
#
# La branch 18.0-parity migra el module-set de v15 (sin la arquitectura de
# Manual Currency Rate / EDI CAEA / etc. construida sobre el branch 18.0
# original). El entorno de staging de Odoo.sh reutiliza una base ya migrada
# a v18 (no una copia limpia de produccion v15), asi que puede traer
# instalados modulos que en esta branch ya no existen en el filesystem.
#
# migrate-update.sh marca esos modulos como 'uninstalled' en ir_module_module
# (comparando contra el filesystem), pero eso NO borra las vistas/datos que
# esos modulos ya habian creado -- mismo patron que las secciones 1, 8 y 9 de
# la migracion 18.0.0.30. Sin este limpiado, Odoo intenta renderizar vistas
# que referencian campos que el registry ya no conoce (OwlError /
# "field is undefined").


def migrate(cr, version):
    print("[wall pre-18.0.0.31] Iniciando limpieza de residuos MCR nueva (18.0-parity)")

    excluded_modules = [
        # gc-odoo-account: arquitectura MCR nueva, fuera del module-set v15
        "manual_currency_rate",
        "manual_currency_rate_invoice",
        "manual_currency_rate_purchase",
        "manual_currency_rate_sale",
        "l10n_ar_edi_caea",
        "account_move_pricelist",
        "product_multi_currency",
        "rusty_check_payment_import",
        "account_invoice_purchase_picking_selection",
        "l10n_ar_bna",
        # tnet-addons-wall: feature nueva de TC en pedidos confirmados
        "wall_sale_currency_rate",
    ]

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
        (excluded_modules,),
    )
    print(f"[wall pre-18.0.0.31] Vistas de modulos MCR nueva eliminadas: {cr.rowcount}")

    cr.execute(
        "DELETE FROM ir_model_data WHERE module = ANY(%s)",
        (excluded_modules,),
    )
    print(f"[wall pre-18.0.0.31] ir_model_data de modulos MCR nueva eliminados: {cr.rowcount}")

    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'uninstalled'
         WHERE name = ANY(%s)
           AND state IN ('installed', 'to upgrade', 'to install', 'to remove')
        """,
        (excluded_modules,),
    )
    print(f"[wall pre-18.0.0.31] Modulos MCR nueva desinstalados en ir_module_module: {cr.rowcount}")

    print("[wall pre-18.0.0.31] Limpieza completada.")
