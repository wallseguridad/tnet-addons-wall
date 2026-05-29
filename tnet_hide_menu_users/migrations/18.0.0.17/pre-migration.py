# Pre-migration 18.0.0.17: limpiar cache de asset bundles de v15.
# Los bundles generados en v15 quedan en ir.attachment con URLs y hashes
# que ya no coinciden con los archivos de v18. Al cargar el frontend,
# el browser intenta resolver rutas inexistentes (ej: jsvat.js de
# partner_autocomplete) y el OWL lifecycle falla con AssetsLoadingError.
# Al borrarlos aquí Odoo los regenera fresh durante el upgrade.
def migrate(cr, version):
    cr.execute("""
        DELETE FROM ir_attachment
         WHERE url LIKE '/web/assets/%'
            OR name ~ '\.(assets\.|min\.js|min\.css)'
    """)
    print(f"[wall 18.0.0.17] Asset bundles v15 eliminados: {cr.rowcount}")
