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
    wall_cost = fields.Float(string='Wall Cost',
                             compute='_compute_wall_cost',
                             inverse='_set_wall_cost',
                             search='_search_wall_cost',
                             digits='Product Price',
                             groups='base.group_user')

    @api.depends_context('company')
    @api.depends('product_variant_ids.wall_cost')
    def _compute_wall_cost(self):
        self._compute_template_field_from_variant_field('wall_cost')

    def _set_wall_cost(self):
        self._set_product_variant_field('wall_cost')

    def _search_wall_cost(self, operator, value):
        return [('product_variant_ids.wall_cost', operator, value)]

    def _get_related_fields_variant_template(self):
        return super()._get_related_fields_variant_template() + ['wall_cost']

    def write(self, vals):
        res = super().write(vals)
        if 'property_cost_currency_id' in vals:
            self.product_variant_ids._update_standard_price_from_wall_cost()
        return res

    @api.onchange('property_currency_id')
    def _onchange_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        if self.property_currency_id:
            self.currency_id = self.property_currency_id.id
        else:
            self.currency_id = self.company_id.sudo().currency_id.id or main_company.currency_id.id

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
        # standard_price is always in the company currency: it is derived from wall_cost,
        # which is the one expressed in property_cost_currency_id.
        for template in self:
            template.cost_currency_id = template.env.company.currency_id.id
