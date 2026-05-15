# -*- coding: utf-8 -*-
"""Runtime schema guards for the v15 -> v18 migration staging DB.

These guards are intentionally placed in an installed, owned module that depends
only on ``base``.  Odoo.sh can enter a state where the registry already knows a
stored field from an external addon, but the corresponding SQL column is still
missing because the defensive migration script did not run in the path used
(manual module updates, aborted upgrades, etc.).  Running these idempotent DDLs
from ``_auto_init`` makes the columns exist before normal HTTP reads start.
"""

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            """
            ALTER TABLE IF EXISTS res_company
            ADD COLUMN IF NOT EXISTS reconcile_on_company_currency BOOLEAN NOT NULL DEFAULT FALSE
            """
        )
        return super()._auto_init()


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            """
            ALTER TABLE IF EXISTS account_account
            ADD COLUMN IF NOT EXISTS is_monetary BOOLEAN
            """
        )
        return super()._auto_init()


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            """
            ALTER TABLE IF EXISTS product_product
            ADD COLUMN IF NOT EXISTS bypass_general_discount BOOLEAN
            """
        )
        return super()._auto_init()


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            """
            ALTER TABLE IF EXISTS product_supplierinfo
                ADD COLUMN IF NOT EXISTS replenishment_cost_rule_id INTEGER,
                ADD COLUMN IF NOT EXISTS last_date_price_updated TIMESTAMP
            """
        )
        return super()._auto_init()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _auto_init(self):
        cr = self.env.cr
        cr.execute(
            """
            ALTER TABLE IF EXISTS product_template
                ADD COLUMN IF NOT EXISTS replenishment_cost_rule_id INTEGER,
                ADD COLUMN IF NOT EXISTS replenishment_cost_last_update TIMESTAMP,
                ADD COLUMN IF NOT EXISTS replenishment_base_cost DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS replenishment_base_cost_currency_id INTEGER,
                ADD COLUMN IF NOT EXISTS replenishment_cost_type VARCHAR
            """
        )
        return super()._auto_init()
