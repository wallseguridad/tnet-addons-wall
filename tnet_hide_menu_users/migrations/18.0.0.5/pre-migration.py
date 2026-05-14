# Pre-migration 18.0.0.5: preparar esquema mínimo antes del upgrade global.
#
# Este módulo depende solo de `base`, por lo que sus pre-migrations corren
# temprano en el upgrade. Usamos este punto como pre-parche de compatibilidad
# para módulos de terceros que no podemos modificar directamente.


def migrate(cr, version):
    if not version:
        return

    # ---------------------------------------------------------------------
    # 1. account_ux: columna agregada por código v18 pero ausente en DB v15
    # ---------------------------------------------------------------------
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS reconcile_on_company_currency BOOLEAN NOT NULL DEFAULT FALSE
    """)
    print("[wall 18.0.0.5] res_company.reconcile_on_company_currency asegurada")

    # ---------------------------------------------------------------------
    # 2. account_tax_settlement: tablas de TransientModel requeridas por
    #    ir_autovacuum apenas el registry conoce los modelos.
    # ---------------------------------------------------------------------
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
    print("[wall 18.0.0.5] tablas res_download_files_wizard(_line) aseguradas")

    # ---------------------------------------------------------------------
    # 3. account_ux: XML legacy referencia account.account_invoices.
    #    Si Odoo 18 lo renombró/removió, creamos alias al reporte de factura.
    # ---------------------------------------------------------------------
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
    print("[wall 18.0.0.5] alias account.account_invoices asegurado si era posible")
