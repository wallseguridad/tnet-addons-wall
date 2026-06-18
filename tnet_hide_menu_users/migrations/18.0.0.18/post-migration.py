# Post-migration 18.0.0.18: migrar campos company_dependent de product_replenishment_cost
# y product_planned_price desde ir.property → columnas directas.
#
# En v15, estos campos usaban company_dependent=True: los valores por-registro
# se almacenaban en ir.property, no en la columna de la tabla.
# En v18, pasaron a columnas directas (sin company_dependent).
# Sin esta migración, todos los productos llegan con replenishment_base_cost=0,
# lo que hace que replenishment_cost=0 y los crons no actualizan ni
# standard_price ni list_price.


def _get_field_id(cr, model_name, field_name):
    cr.execute(
        """
        SELECT f.id FROM ir_model_fields f
        JOIN ir_model m ON m.id = f.model_id
        WHERE f.name = %s AND m.model = %s
        LIMIT 1
        """,
        (field_name, model_name),
    )
    row = cr.fetchone()
    return row[0] if row else None


def _migrate_float(cr, model_name, field_name, table, column):
    field_id = _get_field_id(cr, model_name, field_name)
    if not field_id:
        return 0
    cr.execute(
        """
        SELECT res_id, value_float
        FROM ir_property
        WHERE fields_id = %s
          AND res_id IS NOT NULL AND res_id != ''
          AND type = 'float'
          AND value_float IS NOT NULL
        """,
        (field_id,),
    )
    rows = cr.fetchall()
    migrated = 0
    for res_id_str, value_float in rows:
        try:
            record_id = int(res_id_str.split(",")[1])
        except (IndexError, ValueError):
            continue
        cr.execute(
            f"UPDATE {table} SET {column} = %s WHERE id = %s",
            (value_float, record_id),
        )
        migrated += cr.rowcount
    if migrated:
        cr.execute("DELETE FROM ir_property WHERE fields_id = %s", (field_id,))
    print(f"[wall 18.0.0.18] {model_name}.{field_name}: {migrated} registros migrados")
    return migrated


def _migrate_m2o(cr, model_name, field_name, table, column):
    field_id = _get_field_id(cr, model_name, field_name)
    if not field_id:
        return 0
    cr.execute(
        """
        SELECT res_id, value_reference
        FROM ir_property
        WHERE fields_id = %s
          AND res_id IS NOT NULL AND res_id != ''
          AND type = 'many2one'
          AND value_reference IS NOT NULL
        """,
        (field_id,),
    )
    rows = cr.fetchall()
    migrated = 0
    for res_id_str, value_reference in rows:
        try:
            record_id = int(res_id_str.split(",")[1])
            ref_id = int(value_reference.split(",")[1])
        except (IndexError, ValueError):
            continue
        cr.execute(
            f"UPDATE {table} SET {column} = %s WHERE id = %s",
            (ref_id, record_id),
        )
        migrated += cr.rowcount
    if migrated:
        cr.execute("DELETE FROM ir_property WHERE fields_id = %s", (field_id,))
    print(f"[wall 18.0.0.18] {model_name}.{field_name}: {migrated} registros migrados")
    return migrated


def _migrate_char(cr, model_name, field_name, table, column):
    field_id = _get_field_id(cr, model_name, field_name)
    if not field_id:
        return 0
    cr.execute(
        """
        SELECT res_id, value_text
        FROM ir_property
        WHERE fields_id = %s
          AND res_id IS NOT NULL AND res_id != ''
          AND type IN ('char', 'selection', 'text')
          AND value_text IS NOT NULL AND value_text != ''
        """,
        (field_id,),
    )
    rows = cr.fetchall()
    migrated = 0
    for res_id_str, value_text in rows:
        try:
            record_id = int(res_id_str.split(",")[1])
        except (IndexError, ValueError):
            continue
        cr.execute(
            f"UPDATE {table} SET {column} = %s WHERE id = %s",
            (value_text, record_id),
        )
        migrated += cr.rowcount
    if migrated:
        cr.execute("DELETE FROM ir_property WHERE fields_id = %s", (field_id,))
    print(f"[wall 18.0.0.18] {model_name}.{field_name}: {migrated} registros migrados")
    return migrated


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'ir_property'
        )
        """
    )
    if not cr.fetchone()[0]:
        print("[wall 18.0.0.18] ir_property no existe, nada que migrar")
        return

    total = 0

    # product_replenishment_cost
    total += _migrate_float(cr, "product.template", "replenishment_base_cost", "product_template", "replenishment_base_cost")
    total += _migrate_m2o(cr, "product.template", "replenishment_base_cost_currency_id", "product_template", "replenishment_base_cost_currency_id")
    total += _migrate_m2o(cr, "product.template", "replenishment_cost_rule_id", "product_template", "replenishment_cost_rule_id")
    total += _migrate_char(cr, "product.template", "replenishment_cost_type", "product_template", "replenishment_cost_type")

    # product_planned_price
    total += _migrate_float(cr, "product.template", "computed_list_price_manual", "product_template", "computed_list_price_manual")
    total += _migrate_float(cr, "product.template", "sale_margin", "product_template", "sale_margin")
    total += _migrate_float(cr, "product.template", "sale_surcharge", "product_template", "sale_surcharge")
    total += _migrate_float(cr, "product.template", "other_currency_list_price", "product_template", "other_currency_list_price")
    total += _migrate_m2o(cr, "product.template", "other_currency_id", "product_template", "other_currency_id")
    total += _migrate_char(cr, "product.template", "list_price_type", "product_template", "list_price_type")

    print(f"[wall 18.0.0.18] Total migrado ir.property → columnas directas: {total} registros")
