# Migration: v15 → v18
#
# En v15, los campos `company_dependent=True` se almacenaban en `ir.property`.
# En v17/18 el mecanismo cambió: el valor se almacena directamente en la columna
# de la tabla del modelo (gestionado por el ORM con contexto de compañía).
#
# Este script copia los valores de `ir.property` al nuevo mecanismo
# usando el ORM (post-migration = módulo ya cargado, entorno disponible).


def migrate(cr, version):
    if not version:
        # Instalación fresca (no upgrade): no hay datos en ir.property que migrar.
        return

    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Buscar el campo en ir.model.fields
    field = env['ir.model.fields'].search([
        ('name', '=', 'property_profitability_percentage'),
        ('model', '=', 'product.template'),
    ], limit=1)

    if not field:
        return  # el campo ya no existe en el modelo, nada que hacer

    # Buscar todas las propiedades existentes (res_id != False → son por-registro)
    properties = env['ir.property'].search([
        ('fields_id', '=', field.id),
        ('res_id', '!=', False),
    ])

    migrated = 0
    errors = []

    for prop in properties:
        # res_id tiene el formato 'product.template,42'
        try:
            record_id = int(prop.res_id.split(',')[1])
        except (IndexError, ValueError):
            errors.append(f"res_id inválido: {prop.res_id}")
            continue

        company = prop.company_id or env.company
        template = env['product.template'].with_company(company).browse(record_id)

        if not template.exists():
            continue

        try:
            template.property_profitability_percentage = prop.value_float
            migrated += 1
        except Exception as e:
            errors.append(f"product.template id={record_id}: {e}")

    # Eliminar los registros de ir.property migrados
    properties.unlink()

    print(f"[tnet_product_profitability] Migrados: {migrated} valores de property_profitability_percentage")
    if errors:
        print(f"[tnet_product_profitability] Errores ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
