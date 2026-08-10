# Pre-migration 18.0.0.32: limpiar residuos de website_google_tag.
#
# website_google_tag no es un modulo de esta branch (vive en la branch de
# desarrollo separada app-website_google_tag), pero la base de staging trae
# residuos de un build anterior donde si estaba instalado: la vista que
# inyecta <t t-if="website and website.gtm_get_key()..."/> en website.layout
# quedo activa, y el metodo Python gtm_get_key() ya no existe en el registry
# -> AttributeError al renderizar cualquier pagina del sitio web.
#
# Mismo patron que la migracion 18.0.0.31 (residuos de la arquitectura MCR
# nueva), aplicado acá a un modulo de otra branch.


def migrate(cr, version):
    print("[wall pre-18.0.0.32] Iniciando limpieza de residuos website_google_tag")

    excluded_modules = [
        "website_google_tag",
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
    print(f"[wall pre-18.0.0.32] Vistas de website_google_tag eliminadas: {cr.rowcount}")

    cr.execute(
        "DELETE FROM ir_model_data WHERE module = ANY(%s)",
        (excluded_modules,),
    )
    print(f"[wall pre-18.0.0.32] ir_model_data de website_google_tag eliminados: {cr.rowcount}")

    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'uninstalled'
         WHERE name = ANY(%s)
           AND state IN ('installed', 'to upgrade', 'to install', 'to remove')
        """,
        (excluded_modules,),
    )
    print(f"[wall pre-18.0.0.32] website_google_tag desinstalado en ir_module_module: {cr.rowcount}")

    print("[wall pre-18.0.0.32] Limpieza completada.")
