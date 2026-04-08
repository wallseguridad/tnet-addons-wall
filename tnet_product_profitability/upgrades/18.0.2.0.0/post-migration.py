# Migration: v15 → v18
#
# En v15, los campos `company_dependent=True` se almacenaban en `ir.property`.
# En v17/18 el mecanismo cambió: el valor se almacena directamente en la columna
# de la tabla del modelo (gestionado por el ORM con contexto de compañía).
#
# IMPORTANTE: `ir.property` fue eliminado como modelo ORM en v18, pero la
# tabla `ir_property` todavía existe en la DB durante la migración.
# Se usa SQL crudo para leer los valores y el ORM para escribirlos.


def migrate(cr, version):
    if not version:
        return

    # Verificar que la tabla ir_property aún existe en la DB
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'ir_property'
        )
    """)
    if not cr.fetchone()[0]:
        print("[tnet_product_profitability] Tabla ir_property no existe, nada que migrar")
        return

    # Buscar el field_id del campo property_profitability_percentage en ir.model.fields
    cr.execute("""
        SELECT f.id
        FROM ir_model_fields f
        JOIN ir_model m ON m.id = f.model_id
        WHERE f.name = 'property_profitability_percentage'
          AND m.model = 'product.template'
        LIMIT 1
    """)
    row = cr.fetchone()
    if not row:
        print("[tnet_product_profitability] Campo property_profitability_percentage no existe, nada que migrar")
        return
    field_id = row[0]

    # Leer todos los valores de ir_property para este campo (por-registro, no default)
    cr.execute("""
        SELECT res_id, value_float, company_id
        FROM ir_property
        WHERE fields_id = %s
          AND res_id IS NOT NULL
          AND res_id != ''
          AND type = 'float'
    """, (field_id,))
    rows = cr.fetchall()

    if not rows:
        print("[tnet_product_profitability] No hay valores en ir_property para migrar")
        return

    migrated = 0
    errors = []

    for res_id_str, value_float, company_id in rows:
        # res_id tiene el formato 'product.template,42'
        try:
            record_id = int(res_id_str.split(',')[1])
        except (IndexError, ValueError):
            errors.append(f"res_id inválido: {res_id_str}")
            continue

        if value_float is None:
            continue

        # Escribir directamente en la columna de la tabla (v18: columna directa, no ir_property)
        # La columna en product_template se llama igual que el campo
        try:
            cr.execute("""
                UPDATE product_template
                SET property_profitability_percentage = %s
                WHERE id = %s
            """, (value_float, record_id))
            if cr.rowcount:
                migrated += 1
        except Exception as e:
            errors.append(f"product.template id={record_id}: {e}")

    # Limpiar ir_property para este campo
    cr.execute("DELETE FROM ir_property WHERE fields_id = %s", (field_id,))

    print(f"[tnet_product_profitability] Migrados: {migrated} valores de property_profitability_percentage")
    if errors:
        print(f"[tnet_product_profitability] Errores ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
