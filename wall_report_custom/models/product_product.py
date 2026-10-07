from odoo import fields, models, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_multiline_description_sale(self):
        # name = super().get_product_multiline_description_sale()
        return self.name

    def _get_report_line_text(self, label):
        """Texto de una línea de venta o factura sin el producto.

        Odoo guarda en la línea el nombre del producto seguido del texto que carga
        el usuario; el formulario los muestra separados y los reportes tienen que
        hacer lo mismo. Si la línea no tiene texto propio el resultado es vacío.
        """
        label = (label or '').strip()
        if not self:
            return label
        self.ensure_one()
        # la línea pudo generarse en cualquier idioma y con o sin [código]
        names = set()
        for lang, _lang_name in self.env['res.lang'].get_installed():
            product = self.with_context(lang=lang)
            names.update((
                product.display_name,
                product.with_context(display_default_code=False).display_name,
                product.name,
            ))
        names = {name.strip() for name in names if name}
        for name in sorted(filter(None, names), key=len, reverse=True):
            if name in label:
                label = label.replace(name, '', 1).strip()
                break
        return label
