from odoo import fields, models, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    def _get_computed_name(self):
        self.ensure_one()
        values = super()._get_computed_name()
        if self.partner_id.lang:
            product = self.product_id.with_context(lang=self.partner_id.lang)
        else:
            product = self.product_id
        values = product.name
        return values

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_invoiced_lot_values(self):
        res = super(AccountMove, self)._get_invoiced_lot_values()
        current_invoice_amls = self.invoice_line_ids.filtered(lambda aml: not aml.display_type and aml.product_id and aml.product_id.type in ('consu', 'product') and aml.quantity)
        stock_move_lines = current_invoice_amls.sale_line_ids.move_ids.move_line_ids.filtered(lambda sml: sml.state == 'done' and sml.lot_id).sorted(lambda sml: (sml.date, sml.id))
        for sml in stock_move_lines:
            lot = sml.lot_id.sudo()
            for rec in res:
                if rec["product_name"] == lot.product_id.display_name:
                    rec["product_name"] = lot.product_id.default_code
        return res
        