# Pre-migration 18.0.0.10: asegurar carga de product_replenishment_cost.
#
# En la DB migrada quedaron vistas activas de product_replenishment_cost sobre
# product.supplierinfo, pero el registry v18 no tenía cargado el campo
# product.supplierinfo.replenishment_cost_rule_id. Al abrir Productos, OWL falla
# parseando la lista de proveedores con:
#   "product.supplierinfo"."replenishment_cost_rule_id" field is undefined.
#
# No tocamos el código ADHOC. Marcamos el módulo como pendiente de instalar/
# actualizar para que el registry cargue sus modelos/campos v18.


def migrate(cr, version):
    if not version:
        return

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
    print(f"[wall 18.0.0.10] product_replenishment_cost preparado: {cr.rowcount}")

    # Precrear columnas stored principales para evitar UndefinedColumn si algún
    # proceso lee productos/proveedores antes de que el update del módulo termine.
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
    print("[wall 18.0.0.10] columnas base de product_replenishment_cost aseguradas")
