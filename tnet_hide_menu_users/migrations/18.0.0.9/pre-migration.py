# Pre-migration 18.0.0.9: preparar columna stored de account_ux.
#
# account_ux agrega account.account.is_monetary como Boolean stored/compute.
# Durante el upgrade, al leer contactos (res.partner) Odoo puede cargar campos
# many2one hacia account.account y calcular display_name antes de que account_ux
# haya terminado de crear su columna. Si el registry ya conoce el field pero la
# tabla todavía no, el read falla con:
#   psycopg2.errors.UndefinedColumn: column account_account.is_monetary does not exist


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        ALTER TABLE account_account
        ADD COLUMN IF NOT EXISTS is_monetary BOOLEAN
        """
    )
    print("[wall 18.0.0.9] account_account.is_monetary asegurada")
