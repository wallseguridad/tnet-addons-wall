# Pre-migration 18.0.0.12: restaurar menús nativos de pagos.
#
# Durante la limpieza de account_payment_group (v15) se eliminaron menús que
# apuntaban a acciones del modelo removido account.payment.group. Si esos menús
# eran los XMLIDs nativos de account sobreescritos por el módulo legacy, un
# update posterior de account no necesariamente los recrea.
#
# NOTA: usa SQL directo — en pre-migration, account.payment no está en el
# registry de Odoo (tnet_hide_menu_users depende solo de base y corre primero).
# Cualquier write ORM sobre ir.actions.act_window dispara _check_model, que
# rechaza el modelo aunque el valor ya sea correcto.


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
    action_id = _find_id(cr, module, name, 'ir.actions.act_window')
    if action_id:
        cr.execute("""
            UPDATE ir_act_window
            SET name = %s, res_model = %s, domain = %s, context = %s,
                view_mode = 'list,form', target = 'current'
            WHERE id = %s
        """, (action_name, res_model, domain, context, action_id))
        print(f"[wall 18.0.0.12] act_window {module}.{name} actualizada (id={action_id})")
    else:
        cr.execute("""
            INSERT INTO ir_act_window
                (name, type, res_model, domain, context, view_mode, target,
                 create_uid, write_uid, create_date, write_date)
            VALUES (%s, 'ir.actions.act_window', %s, %s, %s, 'list,form', 'current',
                    1, 1, NOW(), NOW())
            RETURNING id
        """, (action_name, res_model, domain, context))
        action_id = cr.fetchone()[0]
        _upsert_imd(cr, module, name, 'ir.actions.act_window', action_id)
        print(f"[wall 18.0.0.12] act_window {module}.{name} creada (id={action_id})")
    return action_id


def _get_parent_menu_id(cr, *xmlids):
    for xmlid in xmlids:
        module, name = xmlid.split('.')
        menu_id = _find_id(cr, module, name, 'ir.ui.menu')
        if menu_id:
            return menu_id
    return None


def _ensure_menu(cr, module, name, menu_name, parent_id, action_id, sequence=20):
    action_ref = f'ir.actions.act_window,{action_id}'
    menu_id = _find_id(cr, module, name, 'ir.ui.menu')
    if menu_id:
        cr.execute("""
            UPDATE ir_ui_menu
            SET name = %s, parent_id = %s, action = %s, sequence = %s, active = TRUE
            WHERE id = %s
        """, (menu_name, parent_id, action_ref, sequence, menu_id))
        print(f"[wall 18.0.0.12] menú {module}.{name} actualizado (id={menu_id})")
    else:
        cr.execute("""
            INSERT INTO ir_ui_menu
                (name, parent_id, action, sequence, active, create_uid, write_uid, create_date, write_date)
            VALUES (%s, %s, %s, %s, TRUE, 1, 1, NOW(), NOW())
            RETURNING id
        """, (menu_name, parent_id, action_ref, sequence))
        menu_id = cr.fetchone()[0]
        _upsert_imd(cr, module, name, 'ir.ui.menu', menu_id)
        print(f"[wall 18.0.0.12] menú {module}.{name} creado (id={menu_id})")


def migrate(cr, version):
    if not version:
        return

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

    print("[wall 18.0.0.12] Menús nativos de pagos restaurados")
