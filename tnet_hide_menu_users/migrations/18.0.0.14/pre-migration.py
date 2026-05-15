# Pre-migration 18.0.0.14: asegurar tablas TransientModel de account_tax_settlement.
#
# res.download_files_wizard y res.download_files_wizard_line son TransientModels
# definidos por account_tax_settlement (ADHOC). En ciertos upgrade paths el
# _auto_init() del módulo no crea las tablas antes de que el autovacuum las busque,
# lo que genera "relation does not exist" en background.
#
# CREATE TABLE IF NOT EXISTS es idempotente — seguro de re-ejecutar.


def migrate(cr, version):
    if not version:
        return

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
    print("[wall 18.0.0.14] tablas res_download_files_wizard(_line) aseguradas")
