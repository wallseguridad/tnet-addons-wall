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

    pricelist_id = fields.Many2one(
        "product.pricelist", string='Pricelist', check_company=True,  # Unrequired company
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="[('id', 'in', partner_pricelist_ids),'|',('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")

    @api.depends('partner_id')
    def _compute_partner_pricelist_ids(self):
        for rec in self:
            if rec.partner_id and rec.partner_id.pricelist_ids:
                rec.partner_pricelist_ids = rec.partner_id.pricelist_ids

            else:
                rec.partner_pricelist_ids = self.env['product.pricelist'].search([
                ])
                
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SalePricelist, self).onchange_partner_id()
        values = {}
        self.pricelist_id = False
        if 'website_id' in self.env.context:
            company = self.env.company.id
            res = self.env['product.pricelist']._get_partner_pricelist_multi(self.ids, company_id=company)
            for p in self:
                p.pricelist_id = res.get(p.id)
        if self.partner_pricelist_ids:
            for pr_list in self.partner_id.pricelist_ids:
                values['pricelist_id'] = (pr_list.id if pr_list else False)
            self.update(values)
        return res


class PricelistInherit(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.user.has_group('base.group_portal') and self.env.user.partner_id.pricelist_ids.ids:
            args.append(('id', 'in', self.env.user.partner_id.pricelist_ids.ids))
        res = super(PricelistInherit, self)._search(args, offset=offset, limit=limit,
                                                    order=order, count=count, access_rights_uid=access_rights_uid)
        return res
