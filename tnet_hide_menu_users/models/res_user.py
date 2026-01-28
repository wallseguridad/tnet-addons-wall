# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(ResUsers, self).create(vals)

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        for menu in self.hide_menu_ids:
            menu.write({'restrict_user_ids': [(4, self.id)]})
        self.clear_caches()
        return res

    def _get_is_admin(self):
        for rec in self:
            rec.is_admin = False
            if rec.id == self.env.ref('base.user_admin').id:
                rec.is_admin = True

    hide_menu_ids = fields.Many2many(comodel_name='ir.ui.menu',
                                     relation='users_hide_menu',
                                     column1='user_id',
                                     column2='menu_id',
                                     string="Menus", store=True)
    is_admin = fields.Boolean(compute=_get_is_admin)


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    restrict_user_ids = fields.Many2many(comodel_name='res.users',
                                         relation='users_hide_menu',
                                         column1='menu_id',
                                         column2='user_id',
                                         string='Restrict Users')