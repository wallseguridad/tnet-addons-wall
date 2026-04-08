# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api


class ResPartnerPricelist(models.Model):
    _inherit = 'res.partner'

    pricelist_ids = fields.Many2many(
        "product.pricelist", string='Allowed Pricelists')


class SalePricelist(models.Model):
    _inherit = 'sale.order'

    partner_pricelist_ids = fields.Many2many(
        "product.pricelist", compute='_compute_partner_pricelist_ids')

    @api.depends('partner_id')
    def _compute_partner_pricelist_ids(self):
        for rec in self:
            if rec.partner_id and rec.partner_id.pricelist_ids:
                rec.partner_pricelist_ids = rec.partner_id.pricelist_ids
            else:
                rec.partner_pricelist_ids = self.env['product.pricelist'].search([])

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SalePricelist, self).onchange_partner_id()
        values = {}
        self.pricelist_id = False
        if self.partner_pricelist_ids:
            for pr_list in self.partner_id.pricelist_ids:
                values['pricelist_id'] = (pr_list.id if pr_list else False)
            self.update(values)
        return res


class PricelistInherit(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        # v18: firma sin count ni access_rights_uid
        if self.env.user.has_group('base.group_portal') and self.env.user.partner_id.pricelist_ids.ids:
            domain = list(domain) + [('id', 'in', self.env.user.partner_id.pricelist_ids.ids)]
        return super()._search(domain, offset=offset, limit=limit, order=order)
