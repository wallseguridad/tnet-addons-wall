from odoo import fields, models, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_multiline_description_sale(self):
        # name = super().get_product_multiline_description_sale()
        return self.name

    def _get_report_line_text(self, label):
        """Texto de una línea de venta o factura tal como lo muestra el formulario.

        Odoo guarda en la línea el nombre del producto seguido del texto que carga
        el usuario, y el formulario muestra debajo del producto lo que queda al
        quitarle su nombre completo ("[código] nombre"). Los reportes tienen que
        imprimir exactamente eso: si en el formulario no se ve texto, el
        resultado es vacío.
        """
        label = (label or '').strip()
        if not self:
            return label
        self.ensure_one()
        # Solo se quita el nombre completo, igual que el widget del formulario. Una
        # línea que guarda el nombre sin [código] se ve en pantalla y debe imprimirse.
        names = set()
        for lang, _lang_name in self.env['res.lang'].get_installed():
            product = self.with_context(lang=lang)
            names.update((product.display_name, product.product_tmpl_id.display_name))
        names = {name.strip() for name in names if name}
        for name in sorted(filter(None, names), key=len, reverse=True):
            if name in label:
                label = label.replace(name, '', 1).strip()
                break
        return label
