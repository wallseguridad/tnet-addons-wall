# Pre-migration 18.0.0.30: consolidación de todas las pre-migrations v15→v18.
#
# Consolida las versiones 18.0.0.0 a 18.0.0.17 en un único script.
# Diseñado para correr también en instalación fresca (sin `if not version: return`).
#
# Este módulo depende solo de `base`, por lo que corre PRIMERO en el orden de
# carga — antes que account, account_ux, sale, OCA, etc.

import json


# =============================================================================
# SECCIÓN 1 (ex 18.0.0.0): Limpieza exhaustiva de vistas y datos huérfanos
# =============================================================================

def _seccion_1_limpieza_vistas(cr):
    print("[wall pre-18.0.0.30] === Sección 1: limpieza de vistas y datos huérfanos ===")

    # -------------------------------------------------------------------------
    # 1.1. Eliminar vistas inherited cuya vista PADRE ya no existe en la DB
    #      (huérfanas absolutas — inherit_id apunta a un id que no existe)
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_ui_view child
        WHERE child.inherit_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM ir_ui_view parent
              WHERE parent.id = child.inherit_id
          )
    """)
    print(f"[wall pre-18.0.0.30] Vistas huérfanas (padre inexistente): {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 1.2. Eliminar vistas inherited que NO están en ir_model_data
    #      Estas son views "fantasma" de v15 sin trackeabilidad de módulo.
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE inherit_id IS NOT NULL
          AND id NOT IN (
              SELECT res_id FROM ir_model_data WHERE model = 'ir.ui.view'
          )
    """)
    print(f"[wall pre-18.0.0.30] Vistas inherited sin ir_model_data (fantasmas v15): {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 1.3. Eliminar vistas inherited de modelos removidos/restructurados en v16/v17/v18
    # -------------------------------------------------------------------------
    removed_models = [
        'account.change.currency',
        'account.invoice',
        'account.invoice.line',
        'account.bank.statement',
        'account.bank.statement.cashbox',
        'account.cash.rounding',
        'account.register.payments',
        'account.invoice.report',
        'mail.compose.message',
        'sale.advance.payment.inv',
        'stock.inventory',
        'stock.inventory.line',
        'account.payment.group',
    ]
    cr.execute(
        "DELETE FROM ir_ui_view WHERE model = ANY(%s) AND inherit_id IS NOT NULL",
        (removed_models,)
    )
    print(f"[wall pre-18.0.0.30] Vistas inherited de modelos removidos: {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 1.4. Eliminar vistas inherited que referencian acciones/métodos inexistentes en v18
    # -------------------------------------------------------------------------
    removed_references = [
        'action_open_reconcile',
        'action_open_reconcile_statement',
        'action_open_bank_statement',
        'action_register_payment',
        'action_invoice_sent',
        'do_merge',
        'account_invoice_action',
        'action_open_related_document',
        'l10n_latam_check_number',
        '1-line.discount / 100.0',
        'tax_groups_totals',
        'invoice_status_posted',
    ]
    for ref in removed_references:
        cr.execute("""
            DELETE FROM ir_ui_view
            WHERE inherit_id IS NOT NULL
              AND arch_db::text LIKE %s
        """, (f'%{ref}%',))
        if cr.rowcount:
            print(f"[wall pre-18.0.0.30] Vistas con referencia a '{ref}': {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 1.5. Eliminar vistas de módulos que desaparecieron en v17/v18 (con CTE recursivo)
    # -------------------------------------------------------------------------
    gone_modules = [
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
        'account_withholding',
        'account_withholding_automatic',
        'meli_oerp',
        'meli_oerp_accounting',
        'meli_oerp_multiple',
        'meli_oerp_premium',
        'meli_oerp_stock',
        'odoo_connector_api',
        'account_payment_group',
        'product_brand',
        'product_profitability_fix',
        'purchase_discount',
        'website_price_tax_custom',
        'website_product_custom',
        'website_sale_stock_message',
        'website_sale_product_attachment',
        'website_sale_comparison_hide_price',
        'studio_customization',
        'tnet_manual_currency_rate',
    ]
    cr.execute("""
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
    """, (gone_modules,))
    print(f"[wall pre-18.0.0.30] Vistas de módulos eliminados en v18: {cr.rowcount} eliminadas (con hijos)")

    # -------------------------------------------------------------------------
    # 1.6. Limpiar ir.model.data de módulos que ya no existen
    # -------------------------------------------------------------------------
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = ANY(%s)",
        (gone_modules,)
    )
    print(f"[wall pre-18.0.0.30] ir.model.data de módulos eliminados: {cr.rowcount} registros eliminados")

    # -------------------------------------------------------------------------
    # 1.7. Limpiar acciones de módulos/modelos removidos
    # -------------------------------------------------------------------------
    cr.execute("""
        DELETE FROM ir_act_window
        WHERE binding_model_id IN (
            SELECT id FROM ir_model
            WHERE model = ANY(%s)
        )
    """, (removed_models,))
    print(f"[wall pre-18.0.0.30] Acciones de ventana de modelos removidos: {cr.rowcount} eliminadas")

    # -------------------------------------------------------------------------
    # 1.8. Marcar módulos ausentes como 'uninstalled'
    # -------------------------------------------------------------------------
    cr.execute("""
        UPDATE ir_module_module
        SET state = 'uninstalled'
        WHERE name = ANY(%s)
          AND state IN ('installed', 'to upgrade', 'to remove')
    """, (gone_modules,))
    print(f"[wall pre-18.0.0.30] Módulos marcados como uninstalled: {cr.rowcount}")

    # -------------------------------------------------------------------------
    # 1.9. Marcar módulos ADHOC v15 para upgrade
    # -------------------------------------------------------------------------
    adhoc_modules_to_upgrade = [
        'l10n_ar_account_withholding',
        'l10n_latam_check_adhoc',
    ]
    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to upgrade'
        WHERE name = ANY(%s)
          AND state = 'installed'
    """, (adhoc_modules_to_upgrade,))
    print(f"[wall pre-18.0.0.30] Módulos ADHOC v15 marcados para upgrade: {cr.rowcount}")

    # -------------------------------------------------------------------------
    # 1.10. Borrar vistas DB stale de módulos con XML actualizado en v18
    # -------------------------------------------------------------------------
    modules_stale_views = [
        'website_sale_hide_price',
        'l10n_ar_tax',
        'l10n_ar_sale',
    ]
    for module in modules_stale_views:
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
            print(f"[wall pre-18.0.0.30] Vistas DB stale de '{module}': {deleted_views} borradas (incluyendo hijos)")

    # -------------------------------------------------------------------------
    # 1.11. Registrar account_payment_method bajo l10n_latam_check
    # -------------------------------------------------------------------------
    latam_check_methods = [
        ('new_third_party_checks',    'inbound',  'account_payment_method_new_third_party_checks'),
        ('out_third_party_checks',    'outbound', 'account_payment_method_out_third_party_checks'),
        ('new_own_checks',            'outbound', 'account_payment_method_new_own_checks'),
        ('in_third_party_checks',     'inbound',  'account_payment_method_in_third_party_checks'),
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
            print(f"[wall pre-18.0.0.30] account_payment_method '{code}' registrado bajo l10n_latam_check")

    print("[wall pre-18.0.0.30] Sección 1 completada.")


# =============================================================================
# SECCIÓN 2 (ex 18.0.0.1): Limpiar residuos de account_payment_group
# =============================================================================

def _seccion_2_account_payment_group(cr):
    print("[wall pre-18.0.0.30] === Sección 2: limpiar residuos de account_payment_group ===")

    cr.execute("""
        UPDATE ir_module_module
        SET state = 'uninstalled'
        WHERE name = 'account_payment_group'
          AND state IN ('installed', 'to upgrade', 'to remove')
    """)
    print(f"[wall pre-18.0.0.30] account_payment_group marcado uninstalled: {cr.rowcount}")

    cr.execute("""
        DELETE FROM ir_ui_menu
        WHERE action IN (
            SELECT 'ir.actions.act_window,' || id::text
            FROM ir_act_window
            WHERE res_model = 'account.payment.group'
        )
    """)
    print(f"[wall pre-18.0.0.30] Menús de account.payment.group eliminados: {cr.rowcount}")

    cr.execute("""
        DELETE FROM ir_act_window
        WHERE res_model = 'account.payment.group'
    """)
    print(f"[wall pre-18.0.0.30] ir.actions.act_window de account.payment.group: {cr.rowcount} eliminadas")

    cr.execute("""
        WITH RECURSIVE view_tree AS (
            SELECT id FROM ir_ui_view
            WHERE model = 'account.payment.group'
            UNION ALL
            SELECT child.id FROM ir_ui_view child
            JOIN view_tree parent ON child.inherit_id = parent.id
        )
        DELETE FROM ir_ui_view WHERE id IN (SELECT id FROM view_tree)
    """)
    print(f"[wall pre-18.0.0.30] Vistas de account.payment.group eliminadas (con hijos): {cr.rowcount}")

    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'account_payment_group'
    """)
    print(f"[wall pre-18.0.0.30] ir.model.data de account_payment_group: {cr.rowcount} eliminados")

    print("[wall pre-18.0.0.30] Sección 2 completada.")


# =============================================================================
# SECCIÓN 3 (ex 18.0.0.2): Restaurar social_media
# =============================================================================

def _seccion_3_social_media(cr):
    print("[wall pre-18.0.0.30] === Sección 3: restaurar social_media ===")

    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to install'
        WHERE name = 'social_media'
          AND state = 'uninstalled'
    """)
    print(f"[wall pre-18.0.0.30] social_media marcado para reinstalar: {cr.rowcount}")


# =============================================================================
# SECCIÓN 4 (ex 18.0.0.3 + 18.0.0.11): Limpiar vistas con invoice_status_posted
# =============================================================================

def _seccion_4_invoice_status_posted(cr):
    print("[wall pre-18.0.0.30] === Sección 4: limpiar vistas con invoice_status_posted ===")

    cr.execute(
        """
        WITH RECURSIVE target AS (
            SELECT id
              FROM ir_ui_view
             WHERE inherit_id IS NOT NULL
               AND arch_db::text LIKE '%invoice_status_posted%'
            UNION ALL
            SELECT child.id
              FROM ir_ui_view child
              JOIN target parent ON child.inherit_id = parent.id
        ), deleted_imd AS (
            DELETE FROM ir_model_data
             WHERE model = 'ir.ui.view'
               AND res_id IN (SELECT id FROM target)
            RETURNING 1
        )
        DELETE FROM ir_ui_view
         WHERE id IN (SELECT id FROM target)
        """
    )
    print(f"[wall pre-18.0.0.30] Vistas legacy invoice_status_posted eliminadas: {cr.rowcount}")


# =============================================================================
# SECCIÓN 5 (ex 18.0.0.4): Limpiar ir_model_data y menús con act_window inexistente
# =============================================================================

def _seccion_5_restaurar_acciones_pago(cr):
    print("[wall pre-18.0.0.30] === Sección 5: limpiar ir_model_data y menús con act_window inexistente ===")

    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'ir.actions.act_window'
          AND res_id NOT IN (SELECT id FROM ir_act_window)
    """)
    print(f"[wall pre-18.0.0.30] ir_model_data con act_window inexistente: {cr.rowcount} eliminados")

    cr.execute(r"""
        UPDATE ir_ui_menu
        SET action = NULL
        WHERE action ~ '^ir\.actions\.act_window,[0-9]+$'
          AND CAST(split_part(action, ',', 2) AS INTEGER) NOT IN (
              SELECT id FROM ir_act_window
          )
    """)
    print(f"[wall pre-18.0.0.30] ir_ui_menu con acción de pago inválida: {cr.rowcount} limpiados")

    print("[wall pre-18.0.0.30] Sección 5 completada.")


# =============================================================================
# SECCIÓN 6 (ex 18.0.0.5): Preparar esquema mínimo para módulos de terceros
# =============================================================================

def _seccion_6_schema_compat(cr):
    print("[wall pre-18.0.0.30] === Sección 6: preparar esquema de compatibilidad ===")

    # account_ux: columna agregada en v18 ausente en DB v15
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS reconcile_on_company_currency BOOLEAN NOT NULL DEFAULT FALSE
    """)
    print("[wall pre-18.0.0.30] res_company.reconcile_on_company_currency asegurada")

    # account_tax_settlement: tablas de TransientModel
    cr.execute("""
        CREATE TABLE IF NOT EXISTS res_download_files_wizard (
            id SERIAL PRIMARY KEY,
            create_uid INTEGER,
            create_date TIMESTAMP,
            write_uid INTEGER,
            write_date TIMESTAMP,
            show_arba_warning BOOLEAN
        )
    """)
    cr.execute("""
        CREATE TABLE IF NOT EXISTS res_download_files_wizard_line (
            id SERIAL PRIMARY KEY,
            create_uid INTEGER,
            create_date TIMESTAMP,
            write_uid INTEGER,
            write_date TIMESTAMP,
            wizard_id INTEGER,
            txt_filename VARCHAR,
            txt_binary BYTEA
        )
    """)
    print("[wall pre-18.0.0.30] tablas res_download_files_wizard(_line) aseguradas")

    # account_ux: alias account.account_invoices si no existe
    cr.execute("""
        DO $$
        DECLARE
            invoice_report_id INTEGER;
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM ir_model_data
                 WHERE module = 'account'
                   AND name = 'account_invoices'
            ) THEN
                SELECT imd.res_id
                  INTO invoice_report_id
                  FROM ir_model_data imd
                 WHERE imd.module = 'account'
                   AND imd.model = 'ir.actions.report'
                   AND imd.name IN (
                        'account_invoices_without_payment',
                        'action_report_invoice',
                        'account_invoice_report'
                   )
                 ORDER BY CASE imd.name
                            WHEN 'account_invoices_without_payment' THEN 1
                            WHEN 'action_report_invoice' THEN 2
                            ELSE 3
                          END
                 LIMIT 1;

                IF invoice_report_id IS NULL THEN
                    SELECT id
                      INTO invoice_report_id
                      FROM ir_act_report_xml
                     WHERE model = 'account.move'
                       AND (
                            report_name IN (
                                'account.report_invoice',
                                'account.report_invoice_with_payments'
                            )
                            OR report_name ILIKE '%invoice%'
                       )
                     ORDER BY CASE report_name
                                WHEN 'account.report_invoice' THEN 1
                                WHEN 'account.report_invoice_with_payments' THEN 2
                                ELSE 3
                              END,
                              id
                     LIMIT 1;
                END IF;

                IF invoice_report_id IS NOT NULL THEN
                    INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
                    VALUES (
                        'account',
                        'account_invoices',
                        'ir.actions.report',
                        invoice_report_id,
                        TRUE
                    )
                    ON CONFLICT (module, name) DO NOTHING;
                END IF;
            END IF;
        END
        $$
    """)
    print("[wall pre-18.0.0.30] alias account.account_invoices asegurado si era posible")


# =============================================================================
# SECCIÓN 7 (ex 18.0.0.6): Preparar columna de sale_order_general_discount
# =============================================================================

def _seccion_7_sale_general_discount(cr):
    print("[wall pre-18.0.0.30] === Sección 7: columna sale_order_general_discount ===")

    cr.execute("""
        ALTER TABLE product_product
        ADD COLUMN IF NOT EXISTS bypass_general_discount BOOLEAN
    """)
    print("[wall pre-18.0.0.30] product_product.bypass_general_discount asegurada")


# =============================================================================
# SECCIÓN 8 (ex 18.0.0.7): Resolver módulos legacy de localización/checks
# =============================================================================

def _seccion_8_legacy_localizacion(cr):
    print("[wall pre-18.0.0.30] === Sección 8: resolver módulos legacy de localización/checks ===")

    legacy_modules = [
        "l10n_ar_account_withholding",
        "l10n_latam_check_adhoc",
    ]
    replacement_modules = [
        "l10n_ar_withholding",
        "l10n_latam_check",
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
        (legacy_modules,),
    )
    print(f"[wall pre-18.0.0.30] Vistas legacy withholding/check eliminadas: {cr.rowcount}")

    cr.execute(
        "DELETE FROM ir_model_data WHERE module = ANY(%s)",
        (legacy_modules,),
    )
    print(f"[wall pre-18.0.0.30] ir_model_data legacy withholding/check eliminados: {cr.rowcount}")

    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'uninstalled'
         WHERE name = ANY(%s)
           AND state IN ('installed', 'to upgrade', 'to install', 'to remove')
        """,
        (legacy_modules,),
    )
    print(f"[wall pre-18.0.0.30] Módulos legacy withholding/check desinstalados: {cr.rowcount}")

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
    print(f"[wall pre-18.0.0.30] Reemplazos withholding/check preparados: {cr.rowcount}")


# =============================================================================
# SECCIÓN 9 (ex 18.0.0.8): Desactivar vista kanban incompatible de account_multicompany_ux
# =============================================================================

def _seccion_9_kanban_multicompany(cr):
    print("[wall pre-18.0.0.30] === Sección 9: desactivar vista kanban incompatible account_multicompany_ux ===")

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
        "[wall pre-18.0.0.30] Vista kanban dashboard incompatible "
        f"account_multicompany_ux desactivada: {cr.rowcount}"
    )


# =============================================================================
# SECCIÓN 10 (ex 18.0.0.9): Preparar columna stored de account_ux
# =============================================================================

def _seccion_10_account_is_monetary(cr):
    print("[wall pre-18.0.0.30] === Sección 10: columna account_account.is_monetary ===")

    cr.execute(
        """
        ALTER TABLE account_account
        ADD COLUMN IF NOT EXISTS is_monetary BOOLEAN
        """
    )
    print("[wall pre-18.0.0.30] account_account.is_monetary asegurada")


# =============================================================================
# SECCIÓN 11 (ex 18.0.0.10): Asegurar carga de product_replenishment_cost
# =============================================================================

def _seccion_11_product_replenishment_cost(cr):
    print("[wall pre-18.0.0.30] === Sección 11: product_replenishment_cost ===")

    modules = ["product_replenishment_cost"]

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
        (modules,),
    )
    print(f"[wall pre-18.0.0.30] product_replenishment_cost preparado: {cr.rowcount}")

    cr.execute(
        """
        ALTER TABLE product_supplierinfo
            ADD COLUMN IF NOT EXISTS replenishment_cost_rule_id INTEGER,
            ADD COLUMN IF NOT EXISTS last_date_price_updated TIMESTAMP
        """
    )
    cr.execute(
        """
        ALTER TABLE product_template
            ADD COLUMN IF NOT EXISTS replenishment_cost_rule_id INTEGER,
            ADD COLUMN IF NOT EXISTS replenishment_cost_last_update TIMESTAMP,
            ADD COLUMN IF NOT EXISTS replenishment_base_cost DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS replenishment_base_cost_currency_id INTEGER,
            ADD COLUMN IF NOT EXISTS replenishment_cost_type VARCHAR
        """
    )
    print("[wall pre-18.0.0.30] columnas base de product_replenishment_cost aseguradas")


# =============================================================================
# SECCIÓN 12 (ex 18.0.0.12): Restaurar menús nativos de pagos
# =============================================================================

def _find_id(cr, module, name, model):
    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = %s AND name = %s AND model = %s
        LIMIT 1
    """, (module, name, model))
    row = cr.fetchone()
    return row[0] if row else None


def _upsert_imd(cr, module, name, model, res_id):
    cr.execute("""
        INSERT INTO ir_model_data
            (module, name, model, res_id, noupdate, create_date, write_date, create_uid, write_uid)
        VALUES (%s, %s, %s, %s, FALSE, NOW(), NOW(), 1, 1)
        ON CONFLICT (module, name) DO UPDATE SET res_id = EXCLUDED.res_id, model = EXCLUDED.model
    """, (module, name, model, res_id))


def _ensure_action(cr, module, name, action_name, res_model, domain, context):
    name_json = json.dumps({"en_US": action_name})
    action_id = _find_id(cr, module, name, 'ir.actions.act_window')
    if action_id:
        cr.execute("""
            UPDATE ir_act_window
            SET name = %s, res_model = %s, domain = %s, context = %s,
                view_mode = 'list,form', target = 'current'
            WHERE id = %s
        """, (name_json, res_model, domain, context, action_id))
        print(f"[wall pre-18.0.0.30] act_window {module}.{name} actualizada (id={action_id})")
    else:
        cr.execute("""
            INSERT INTO ir_act_window
                (name, type, res_model, domain, context, view_mode, target,
                 create_uid, write_uid, create_date, write_date)
            VALUES (%s, 'ir.actions.act_window', %s, %s, %s, 'list,form', 'current',
                    1, 1, NOW(), NOW())
            RETURNING id
        """, (name_json, res_model, domain, context))
        action_id = cr.fetchone()[0]
        _upsert_imd(cr, module, name, 'ir.actions.act_window', action_id)
        print(f"[wall pre-18.0.0.30] act_window {module}.{name} creada (id={action_id})")
    return action_id


def _get_parent_menu_id(cr, *xmlids):
    for xmlid in xmlids:
        module, name = xmlid.split('.')
        menu_id = _find_id(cr, module, name, 'ir.ui.menu')
        if menu_id:
            return menu_id
    return None


def _ensure_menu(cr, module, name, menu_name, parent_id, action_id, sequence=20):
    name_json = json.dumps({"en_US": menu_name})
    action_ref = f'ir.actions.act_window,{action_id}'
    menu_id = _find_id(cr, module, name, 'ir.ui.menu')
    if menu_id:
        cr.execute("""
            UPDATE ir_ui_menu
            SET name = %s, parent_id = %s, action = %s, sequence = %s, active = TRUE
            WHERE id = %s
        """, (name_json, parent_id, action_ref, sequence, menu_id))
        print(f"[wall pre-18.0.0.30] menú {module}.{name} actualizado (id={menu_id})")
    else:
        cr.execute("""
            INSERT INTO ir_ui_menu
                (name, parent_id, action, sequence, active, create_uid, write_uid, create_date, write_date)
            VALUES (%s, %s, %s, %s, TRUE, 1, 1, NOW(), NOW())
            RETURNING id
        """, (name_json, parent_id, action_ref, sequence))
        menu_id = cr.fetchone()[0]
        _upsert_imd(cr, module, name, 'ir.ui.menu', menu_id)
        print(f"[wall pre-18.0.0.30] menú {module}.{name} creado (id={menu_id})")


def _seccion_12_menus_pagos(cr):
    print("[wall pre-18.0.0.30] === Sección 12: restaurar menús nativos de pagos ===")

    customer_action_id = _ensure_action(
        cr, 'account', 'action_account_payments',
        'Customer Payments', 'account.payment',
        "[('partner_type', '=', 'customer')]",
        "{'default_partner_type': 'customer', 'default_payment_type': 'inbound'}",
    )
    supplier_action_id = _ensure_action(
        cr, 'account', 'action_account_payments_payable',
        'Vendor Payments', 'account.payment',
        "[('partner_type', '=', 'supplier')]",
        "{'default_partner_type': 'supplier', 'default_payment_type': 'outbound'}",
    )

    receivable_parent_id = _get_parent_menu_id(
        cr, 'account.menu_finance_receivables', 'account.menu_finance'
    )
    payable_parent_id = _get_parent_menu_id(
        cr, 'account.menu_finance_payables', 'account.menu_finance'
    )

    if receivable_parent_id:
        _ensure_menu(
            cr, 'account', 'menu_action_account_payments_receivable',
            'Payments', receivable_parent_id, customer_action_id, 20,
        )
    if payable_parent_id:
        _ensure_menu(
            cr, 'account', 'menu_action_account_payments_payable',
            'Payments', payable_parent_id, supplier_action_id, 20,
        )

    print("[wall pre-18.0.0.30] Sección 12 completada.")


# =============================================================================
# SECCIÓN 13 (ex 18.0.0.14): Asegurar tablas TransientModel de account_tax_settlement
# =============================================================================

def _seccion_13_account_tax_settlement(cr):
    print("[wall pre-18.0.0.30] === Sección 13: tablas TransientModel de account_tax_settlement ===")

    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to upgrade'
        WHERE name = 'account_tax_settlement'
          AND state = 'installed'
    """)
    if cr.rowcount:
        print("[wall pre-18.0.0.30] account_tax_settlement marcado para upgrade")

    cr.execute("""
        CREATE TABLE IF NOT EXISTS res_download_files_wizard (
            id SERIAL PRIMARY KEY,
            create_uid INTEGER,
            create_date TIMESTAMP,
            write_uid INTEGER,
            write_date TIMESTAMP,
            show_arba_warning BOOLEAN
        )
    """)
    cr.execute("""
        CREATE TABLE IF NOT EXISTS res_download_files_wizard_line (
            id SERIAL PRIMARY KEY,
            create_uid INTEGER,
            create_date TIMESTAMP,
            write_uid INTEGER,
            write_date TIMESTAMP,
            wizard_id INTEGER,
            txt_filename VARCHAR,
            txt_binary BYTEA
        )
    """)
    print("[wall pre-18.0.0.30] tablas res_download_files_wizard(_line) aseguradas")


# =============================================================================
# SECCIÓN 14 (ex 18.0.0.15): Limpiar group_ids legacy en menús de pagos
# =============================================================================

def _seccion_14_limpiar_group_ids_menus_pagos(cr):
    print("[wall pre-18.0.0.30] === Sección 14: limpiar group_ids legacy en menús de pagos ===")

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
    print(f"[wall pre-18.0.0.30] group_ids legacy removidos de menús de pagos: {cr.rowcount} filas")


# =============================================================================
# SECCIÓN 15 (ex 18.0.0.16): Forzar instalación de módulos post-upgrade
# =============================================================================

def _seccion_15_modulos_post_upgrade(cr):
    print("[wall pre-18.0.0.30] === Sección 15: forzar instalación de módulos post-upgrade ===")

    modules_to_install = [
        'wall_sale_compat',
        'l10n_ar_payment_bundle',
    ]

    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to install'
        WHERE name = ANY(%s)
          AND state = 'uninstalled'
    """, (modules_to_install,))
    print(f"[wall pre-18.0.0.30] módulos marcados como 'to install': {cr.rowcount} ({', '.join(modules_to_install)})")


# =============================================================================
# SECCIÓN 16 (ex 18.0.0.17): Limpiar cache de asset bundles de v15
# =============================================================================

def _seccion_16_limpiar_asset_bundles(cr):
    print("[wall pre-18.0.0.30] === Sección 16: limpiar asset bundles de v15 ===")

    cr.execute("""
        DELETE FROM ir_attachment
         WHERE url LIKE '/web/assets/%'
            OR name ~ '\.(assets\.|min\.js|min\.css)'
    """)
    print(f"[wall pre-18.0.0.30] Asset bundles v15 eliminados: {cr.rowcount}")


# =============================================================================
# ENTRY POINT
# =============================================================================

def migrate(cr, version):
    print("[wall pre-18.0.0.30] Iniciando pre-migration consolidada v15→v18")

    _seccion_1_limpieza_vistas(cr)
    _seccion_2_account_payment_group(cr)
    _seccion_3_social_media(cr)
    _seccion_4_invoice_status_posted(cr)
    _seccion_5_restaurar_acciones_pago(cr)
    _seccion_6_schema_compat(cr)
    _seccion_7_sale_general_discount(cr)
    _seccion_8_legacy_localizacion(cr)
    _seccion_9_kanban_multicompany(cr)
    _seccion_10_account_is_monetary(cr)
    _seccion_11_product_replenishment_cost(cr)
    _seccion_12_menus_pagos(cr)
    _seccion_13_account_tax_settlement(cr)
    _seccion_14_limpiar_group_ids_menus_pagos(cr)
    _seccion_15_modulos_post_upgrade(cr)
    _seccion_16_limpiar_asset_bundles(cr)

    print("[wall pre-18.0.0.30] Pre-migration consolidada completada.")
