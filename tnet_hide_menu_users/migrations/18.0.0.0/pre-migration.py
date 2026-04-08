# Pre-migration: limpieza exhaustiva de vistas y datos huérfanos antes del upgrade v15→v18
#
# Este módulo depende solo de `base`, por lo que este script corre PRIMERO
# en el orden de carga — antes que account, account_ux, sale, OCA, etc.
#
# Sin esta limpieza, el upgrade falla con ParseError al intentar cargar vistas
# XML de los módulos actualizados sobre datos de v15 que ya no son compatibles.


def migrate(cr, version):
    if not version:
        return

    # -------------------------------------------------------------------------
    # 1. Eliminar vistas inherited cuya vista PADRE ya no existe en la DB
    #    (huérfanas absolutas — inherit_id apunta a un id que no existe)
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_ui_view child
        WHERE child.inherit_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM ir_ui_view parent
              WHERE parent.id = child.inherit_id
          )
    """)
    print(f"[wall pre-migration] Vistas huérfanas (padre inexistente): {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 2. Eliminar vistas inherited de modelos que fueron removidos o
    #    restructurados en Odoo v16/v17/v18
    # -------------------------------------------------------------------------
    removed_models = [
        'account.change.currency',       # eliminado en v18, ADHOC lo recrea limpio
        'account.invoice',               # fusionado en account.move (v13)
        'account.invoice.line',          # fusionado en account.move.line (v13)
        'account.bank.statement',        # restructurado en v15/v16
        'account.bank.statement.cashbox',
        'account.cash.rounding',
        'account.register.payments',     # reemplazado por account.payment.register
        'account.invoice.report',        # vista eliminada
        'mail.compose.message',          # restructurado
        'sale.advance.payment.inv',      # restructurado en v16
        'stock.inventory',               # eliminado en v16 (reemplazado por quants)
        'stock.inventory.line',          # eliminado en v16
    ]
    cr.execute(
        "DELETE FROM ir_ui_view WHERE model = ANY(%s) AND inherit_id IS NOT NULL",
        (removed_models,)
    )
    print(f"[wall pre-migration] Vistas inherited de modelos removidos: {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 3. Eliminar vistas inherited que referencian acciones/métodos que ya
    #    no existen en v18 (causan "is not a valid action" al validar la vista)
    # -------------------------------------------------------------------------
    removed_references = [
        'action_open_reconcile',          # eliminado de res.partner en v18
        'action_open_reconcile_statement',
        'action_open_bank_statement',
        'action_register_payment',        # reemplazado
        'action_invoice_sent',
        'do_merge',
        'account_invoice_action',
        'action_open_related_document',   # eliminado/renombrado en v18 de account.move.line
        'l10n_latam_check_number',        # removido de account.payment.register en v18
        '1-line.discount / 100.0',        # l10n_ar_sale: t-esc removido del portal template en v18
    ]
    for ref in removed_references:
        cr.execute("""
            DELETE FROM ir_ui_view
            WHERE inherit_id IS NOT NULL
              AND arch_db::text LIKE %s
        """, (f'%{ref}%',))
        if cr.rowcount:
            print(f"[wall pre-migration] Vistas con referencia a '{ref}': {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 4. Desactivar vistas de módulos que desaparecieron en v18
    #    (fusionados en otros módulos — Odoo no los va a reinstalar)
    # -------------------------------------------------------------------------
    gone_modules = [
        # módulos Odoo nativos fusionados/eliminados en v17/v18
        'account_edi_facturx',
        'account_predictive_bills',
        'account_reports_tax_reminder',
        'barcodes_mobile',
        'fetchmail',
        'fetchmail_gmail',
        'payment_transfer',
        'purchase_enterprise',
        'purchase_stock_enterprise',
        'sale_enterprise',
        'stock_account_enterprise',
        'web_dashboard',
        'web_kanban_gauge',
        'website_form_project',
        'social_media',
        # módulos ADHOC v15 reemplazados por módulos nativos Odoo en v18
        'account_withholding',            # reemplazado por l10n_ar_withholding (nativo)
        'account_withholding_automatic',  # fusionado en l10n_ar_withholding
        # módulos MercadoLibre — pendientes migración o sin archivos en v18
        'meli_oerp',
        'meli_oerp_accounting',
        'meli_oerp_multiple',
        'meli_oerp_premium',
        'meli_oerp_stock',
        'odoo_connector_api',             # conector usado por meli_oerp
        # módulos GauchoCode — pendientes migración a v18
        'partner_type',
        'product_brand',
        'product_profitability_fix',
        'product_sap_code',
        'purchase_discount',
        # módulos custom v15 pendientes de migración
        'website_price_tax_custom',
        'website_product_custom',
        'website_sale_stock_message',
        'website_sale_product_attachment',
        'website_sale_comparison_hide_price',
        'studio_customization',
        'tnet_manual_currency_rate',      # reemplazado por manual_currency_rate (gc)
        'tnet_product_multi_currency',    # reemplazado por product_multi_currency (gc)
    ]
    # Las vistas no tienen columna `module` directa — está en ir_model_data
    cr.execute("""
        UPDATE ir_ui_view SET active = FALSE
        WHERE active = TRUE
          AND id IN (
              SELECT res_id FROM ir_model_data
              WHERE model = 'ir.ui.view'
                AND module = ANY(%s)
          )
    """, (gone_modules,))
    print(f"[wall pre-migration] Vistas de módulos eliminados en v18: {cr.rowcount} desactivadas")

    # -------------------------------------------------------------------------
    # 5. Limpiar ir.model.data de módulos que ya no existen
    #    (evita que Odoo intente resolver external IDs inexistentes)
    # -------------------------------------------------------------------------
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = ANY(%s)",
        (gone_modules,)
    )
    print(f"[wall pre-migration] ir.model.data de módulos eliminados: {cr.rowcount} registros eliminados")

    # -------------------------------------------------------------------------
    # 6. Limpiar acciones de módulos que ya no existen
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_act_window
        WHERE binding_model_id IN (
            SELECT id FROM ir_model
            WHERE model = ANY(%s)
        )
    """, (removed_models,))
    print(f"[wall pre-migration] Acciones de ventana de modelos removidos: {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 7. Marcar módulos ausentes como 'uninstalled' en ir_module_module
    #    Si un módulo está como 'installed'/'to upgrade' pero sus archivos no
    #    existen en el addons path de v18, Odoo reporta "inconsistent states"
    #    y todos sus dependientes también quedan bloqueados.
    # -------------------------------------------------------------------------
    cr.execute("""
        UPDATE ir_module_module
        SET state = 'uninstalled'
        WHERE name = ANY(%s)
          AND state IN ('installed', 'to upgrade', 'to remove')
    """, (gone_modules,))
    print(f"[wall pre-migration] Módulos marcados como uninstalled: {cr.rowcount}")

    # -------------------------------------------------------------------------
    # 8. Borrar vistas DB de módulos que tienen XML actualizado pero vistas
    #    viejas en DB incompatibles con la vista padre de v18.
    #    Odoo valida el arch en DB ANTES de aplicar el XML nuevo — si el arch
    #    viejo tiene un xpath que ya no existe en el padre v18, el upgrade falla.
    #    Al borrar las vistas, Odoo las crea fresh desde el XML nuevo.
    # -------------------------------------------------------------------------
    modules_stale_views = [
        'website_sale_hide_price',   # xpath css_quantity cambió en v18
        'l10n_ar_tax',               # l10n_latam_check_number removido del XML en v18
        'l10n_ar_sale',              # múltiples views stale (t-esc, t-call) removidos en v18
    ]
    for module in modules_stale_views:
        # Primero borrar hijos que heredan de las vistas del módulo (FK constraint)
        # usando CTE recursivo para cubrir herencias anidadas
        cr.execute("""
            WITH RECURSIVE view_tree AS (
                SELECT id FROM ir_ui_view
                WHERE id IN (
                    SELECT res_id FROM ir_model_data
                    WHERE model = 'ir.ui.view' AND module = %s
                )
                UNION ALL
                SELECT child.id FROM ir_ui_view child
                JOIN view_tree parent ON child.inherit_id = parent.id
            )
            DELETE FROM ir_ui_view WHERE id IN (SELECT id FROM view_tree)
        """, (module,))
        deleted_views = cr.rowcount
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = %s AND model = 'ir.ui.view'",
            (module,)
        )
        if deleted_views:
            print(f"[wall pre-migration] Vistas DB stale de '{module}': {deleted_views} borradas (incluyendo hijos)")

    # -------------------------------------------------------------------------
    # 9. Registrar account_payment_method existentes bajo l10n_latam_check
    #    En v15 estos métodos los creaba un módulo ADHOC. En v18 los adopta
    #    el módulo nativo l10n_latam_check. Sin ir_model_data que apunte al
    #    registro existente, Odoo intenta INSERT y falla por unique constraint.
    # -------------------------------------------------------------------------
    latam_check_methods = [
        ('new_third_party_checks',  'inbound',  'account_payment_method_new_third_party_checks'),
        ('out_third_party_checks',  'outbound', 'account_payment_method_out_third_party_checks'),
        ('new_own_checks',          'outbound', 'account_payment_method_new_own_checks'),
        ('in_third_party_checks',   'inbound',  'account_payment_method_in_third_party_checks'),
        ('return_third_party_checks', 'outbound', 'account_payment_method_return_third_party_checks'),
    ]
    for code, payment_type, ext_id_name in latam_check_methods:
        cr.execute("""
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate, create_date, write_date, create_uid, write_uid)
            SELECT
                'l10n_latam_check',
                %s,
                'account.payment.method',
                id,
                TRUE,
                NOW(), NOW(), 1, 1
            FROM account_payment_method
            WHERE code = %s AND payment_type = %s
            ON CONFLICT (module, name) DO UPDATE SET res_id = EXCLUDED.res_id
        """, (ext_id_name, code, payment_type))
        if cr.rowcount:
            print(f"[wall pre-migration] account_payment_method '{code}' registrado bajo l10n_latam_check")

    print("[wall pre-migration] Limpieza completada.")
