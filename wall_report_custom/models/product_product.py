from odoo import fields, models, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_multiline_description_sale(self):
        # name = super().get_product_multiline_description_sale()
        return self.name
