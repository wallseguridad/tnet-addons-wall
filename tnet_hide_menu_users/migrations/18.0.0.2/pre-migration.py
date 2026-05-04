# Pre-migration 18.0.0.2: restaurar social_media en instancias existentes.
#
# La pre-migration 18.0.0.0 incluía social_media en gone_modules por error.
# social_media existe en Odoo 18 Enterprise y debe permanecer instalado.
# Su ausencia rompe templates de website (KeyError: 'website' en http_routing.404).


def migrate(cr, version):
    if not version:
        return

    # Marcar social_media como 'to install' para que Odoo lo reinstale.
    # Si el registro no existe en la BD, Odoo lo detecta por filesystem en el upgrade.
    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to install'
        WHERE name = 'social_media'
          AND state = 'uninstalled'
    """)
    print(f"[wall 18.0.0.2] social_media marcado para reinstalar: {cr.rowcount}")
