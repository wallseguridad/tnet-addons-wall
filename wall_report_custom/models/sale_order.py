from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_name_sale_report(self, report_xml_id):
        self.ensure_one()
        if self.company_id.country_id.code == 'AR':
            return 'wall_report_custom.report_saleorder_document'
        return super()._get_name_sale_report(report_xml_id)
