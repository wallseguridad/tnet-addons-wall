# -*- coding: utf-8 -*-
"""Reactiva las vistas de reportes que el upgrade a v18 deja desactivadas.

Las vistas de factura y remito venían con xpath de versiones anteriores, por lo
que el upgrade las desactiva. La actualización del módulo carga el arch ya
migrado pero no toca el campo active, así que hay que reactivarlas acá.

Las dos del remito van juntas: una agrega el encabezado "Código" y la otra la
celda, y con una sola las columnas quedan desalineadas.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

VIEWS = (
    'wall_report_custom.report_invoice_document_inherit',
    'wall_report_custom.report_delivery_document_inherit',
    'wall_report_custom.stock_report_delivery_aggregated_move_lines_inherit',
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    views = env['ir.ui.view']
    for xmlid in VIEWS:
        views |= env.ref(xmlid, raise_if_not_found=False) or env['ir.ui.view']
    inactive = views.filtered(lambda view: not view.active)
    if not inactive:
        return
    try:
        # si algún xpath no aplica, la validación falla: no se corta la
        # actualización, las vistas quedan como estaban y se avisa en el log
        with cr.savepoint():
            inactive.write({'active': True})
    except Exception:
        _logger.exception("[wall_report_custom 18.0.0.1.2] no se pudieron reactivar las vistas: %s",
                          ', '.join(inactive.mapped('key')))
        return
    _logger.info("[wall_report_custom 18.0.0.1.2] vistas reactivadas: %s", ', '.join(inactive.mapped('key')))
