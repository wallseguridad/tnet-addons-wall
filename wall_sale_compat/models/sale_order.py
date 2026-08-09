# -*- coding: utf-8 -*-
from lxml import etree

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != 'form' or not res.get('arch'):
            return res

        # sale_order_general_discount injecta en el context del order_line:
        #   {'default_discount': general_discount, ...}
        # En Odoo 18 OWL evalúa el context antes de que 'general_discount'
        # esté disponible → NameError/EvalError. Reemplazamos con 0.0; el
        # módulo OCA igual recalcula el descuento desde order_id.general_discount.
        arch_bytes = res['arch']
        if isinstance(arch_bytes, bytes):
            arch_bytes = arch_bytes.decode('utf-8')

        arch = etree.XML(arch_bytes)
        changed = False
        for order_line in arch.xpath("//field[@name='order_line'][@context]"):
            context = order_line.attrib.get('context') or ''
            sanitized = context.replace(
                "'default_discount': general_discount, ",
                "'default_discount': 0.0, ",
            ).replace(
                '"default_discount": general_discount, ',
                '"default_discount": 0.0, ',
            )
            if sanitized != context:
                order_line.attrib['context'] = sanitized
                changed = True
        if changed:
            res['arch'] = etree.tostring(arch, encoding='unicode')
        return res
