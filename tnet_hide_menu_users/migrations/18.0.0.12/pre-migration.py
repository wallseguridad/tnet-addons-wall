# Pre-migration 18.0.0.12: restaurar menús nativos de pagos.
#
# Durante la limpieza de account_payment_group (v15) se eliminaron menús que
# apuntaban a acciones del modelo removido account.payment.group. Si esos menús
# eran los XMLIDs nativos de account sobreescritos por el módulo legacy, un
# update posterior de account no necesariamente los recrea porque pueden quedar
# external IDs huérfanos o datos borrados fuera del flujo normal de XML.
#
# Este script crea/actualiza explícitamente las acciones y menús estándar para
# acceder a account.payment desde Contabilidad > Clientes/Proveedores > Pagos.

from odoo import SUPERUSER_ID, api


def _xmlid_record(env, module, name):
    imd = env["ir.model.data"].sudo().search(
        [("module", "=", module), ("name", "=", name)], limit=1
    )
    if not imd:
        return imd, env["ir.ui.menu"]
    try:
        return imd, env[imd.model].sudo().browse(imd.res_id).exists()
    except Exception:
        return imd, env["ir.ui.menu"]


def _ensure_xmlid(env, module, name, model, record):
    IMD = env["ir.model.data"].sudo()
    imd = IMD.search([("module", "=", module), ("name", "=", name)], limit=1)
    vals = {"module": module, "name": name, "model": model, "res_id": record.id, "noupdate": False}
    if imd:
        imd.write(vals)
    else:
        IMD.create(vals)


def _get_parent_menu(env, xmlid_name, fallback_name):
    imd, rec = _xmlid_record(env, "account", xmlid_name)
    if rec:
        return rec
    _imd, rec = _xmlid_record(env, "account", fallback_name)
    return rec if rec else False


def _ensure_action(env, xmlid_name, vals):
    Act = env["ir.actions.act_window"].sudo()
    imd, rec = _xmlid_record(env, "account", xmlid_name)
    if rec and rec._name == "ir.actions.act_window":
        rec.write(vals)
        action = rec
    else:
        if imd:
            imd.unlink()
        action = Act.create(vals)
    _ensure_xmlid(env, "account", xmlid_name, "ir.actions.act_window", action)
    return action


def _ensure_menu(env, xmlid_name, vals):
    Menu = env["ir.ui.menu"].sudo()
    imd, rec = _xmlid_record(env, "account", xmlid_name)
    if rec and rec._name == "ir.ui.menu":
        rec.write(vals)
        menu = rec
    else:
        if imd:
            imd.unlink()
        menu = Menu.create(vals)
    _ensure_xmlid(env, "account", xmlid_name, "ir.ui.menu", menu)
    return menu


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    customer_action = _ensure_action(
        env,
        "action_account_payments",
        {
            "name": "Customer Payments",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": "[('partner_type', '=', 'customer')]",
            "context": "{'default_partner_type': 'customer', 'default_payment_type': 'inbound'}",
            "target": "current",
        },
    )
    supplier_action = _ensure_action(
        env,
        "action_account_payments_payable",
        {
            "name": "Vendor Payments",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": "[('partner_type', '=', 'supplier')]",
            "context": "{'default_partner_type': 'supplier', 'default_payment_type': 'outbound'}",
            "target": "current",
        },
    )

    receivable_parent = _get_parent_menu(env, "menu_finance_receivables", "menu_finance")
    payable_parent = _get_parent_menu(env, "menu_finance_payables", "menu_finance")

    if receivable_parent:
        _ensure_menu(
            env,
            "menu_action_account_payments_receivable",
            {
                "name": "Payments",
                "parent_id": receivable_parent.id,
                "action": f"ir.actions.act_window,{customer_action.id}",
                "sequence": 20,
                "active": True,
            },
        )
    if payable_parent:
        _ensure_menu(
            env,
            "menu_action_account_payments_payable",
            {
                "name": "Payments",
                "parent_id": payable_parent.id,
                "action": f"ir.actions.act_window,{supplier_action.id}",
                "sequence": 20,
                "active": True,
            },
        )

    print("[wall 18.0.0.12] Menús nativos de pagos restaurados")
