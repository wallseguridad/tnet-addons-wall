# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_default_property_currency(self):
        return self.env.ref('base.USD').id if self.env.ref('base.USD') else False

    property_currency_id = fields.Many2one(comodel_name='res.currency',
                                           string='List Price Currency',
                                           default=_get_default_property_currency,
                                           company_dependent=True)
    property_cost_currency_id = fields.Many2one(comodel_name='res.currency',
                                                string='Cost Currency',
                                                default=_get_default_property_currency,
                                                company_dependent=True)

    @api.onchange('property_currency_id')
    def _onchange_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        if self.property_currency_id:
            self.currency_id = self.property_currency_id.id
        else:
            self.currency_id = self.company_id.sudo().currency_id.id or main_company.currency_id.id

    @api.onchange('property_cost_currency_id')
    def _onchange_cost_currency_id(self):
        if self.property_cost_currency_id:
            self.cost_currency_id = self.property_cost_currency_id.id
        else:
            self.cost_currency_id = self.env.company.currency_id.id

    @api.depends('company_id')
    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            if template.property_currency_id:
                template.currency_id = template.property_currency_id.id
            else:
                template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id

    @api.depends_context('company')
    def _compute_cost_currency_id(self):
        for template in self:
            if template.property_cost_currency_id:
                template.cost_currency_id = template.property_cost_currency_id.id
            else:
                template.cost_currency_id = template.env.company.currency_id.id
