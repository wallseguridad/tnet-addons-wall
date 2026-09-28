# -*- coding: utf-8 -*-
"""Move the cost in foreign currency from standard_price to wall_cost.

Until 18.0.0.1.0, standard_price held the cost expressed in property_cost_currency_id
(usually USD), while stock valuation treated it as company currency. From now on:
  - wall_cost        = cost in property_cost_currency_id (the old standard_price value)
  - standard_price   = wall_cost converted to the company currency at today's rate

Writing wall_cost triggers the standard_price update, which goes through stock_account
and creates the revaluation layers for products with stock.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([]):
        products = env['product.product'].with_company(company).with_context(active_test=False).search([])
        migrated = 0
        for product in products:
            cost = product.standard_price
            if not cost or product.wall_cost:
                continue
            product.wall_cost = cost
            migrated += 1
        _logger.info("[tnet_product_multi_currency 18.0.0.2.0] %s: wall_cost migrated on %s products",
                     company.name, migrated)
