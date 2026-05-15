# -*- coding: utf-8 -*-
"""Runtime schema guards for the v15 -> v18 migration staging DB.

All DDL runs inside ResCompany._auto_init() — the only safe anchor here because
tnet_hide_menu_users depends only on `base`.  Inheriting from account.account,
product.product, etc. would fail at _build_model time since those modules are
not guaranteed to be loaded before this one.

The ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS statements are idempotent
and reference the raw table names, so they work regardless of ORM model state.
"""

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _auto_init(self):
        cr = self.env.cr
        # res.company — account_ux stored field
        cr.execute("""
            ALTER TABLE IF EXISTS res_company
            ADD COLUMN IF NOT EXISTS reconcile_on_company_currency BOOLEAN NOT NULL DEFAULT FALSE
        """)
        # account.account — gc-odoo-account stored field
        cr.execute("""
            ALTER TABLE IF EXISTS account_account
            ADD COLUMN IF NOT EXISTS is_monetary BOOLEAN
        """)
        # product.product — sale/purchase addon stored field
        cr.execute("""
            ALTER TABLE IF EXISTS product_product
            ADD COLUMN IF NOT EXISTS bypass_general_discount BOOLEAN
        """)
        # product.supplierinfo — product_replenishment_cost stored fields
        cr.execute("""
            ALTER TABLE IF EXISTS product_supplierinfo
                ADD COLUMN IF NOT EXISTS replenishment_cost_rule_id INTEGER,
                ADD COLUMN IF NOT EXISTS last_date_price_updated TIMESTAMP
        """)
        # product.template — product_replenishment_cost stored fields
        cr.execute("""
            ALTER TABLE IF EXISTS product_template
                ADD COLUMN IF NOT EXISTS replenishment_cost_rule_id INTEGER,
                ADD COLUMN IF NOT EXISTS replenishment_cost_last_update TIMESTAMP,
                ADD COLUMN IF NOT EXISTS replenishment_base_cost DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS replenishment_base_cost_currency_id INTEGER,
                ADD COLUMN IF NOT EXISTS replenishment_cost_type VARCHAR
        """)
        return super()._auto_init()
