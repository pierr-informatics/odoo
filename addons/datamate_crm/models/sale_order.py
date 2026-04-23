# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Domain


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_proposal_notes = fields.Html(
        string='Executive Summary / Proposal Notes',
        help='Custom WYSIWYG notes injected into the PDF proposal by the salesperson.',
    )

    # === Product Catalog: only show CPQ modules ===

    def _get_product_catalog_domain(self):
        domain = super()._get_product_catalog_domain()
        return domain & Domain([('product_tmpl_id.cpq_type', '=', 'module')])

    # === Auto-insert section header for main product on catalog add ===

    def _update_order_line_info(self, product_id, quantity, *, section_id=False, **kwargs):
        """When a CPQ module is added from the catalog, auto-insert a section
        line for its Main Product (if not already present) and place the module
        line inside that section.
        """
        if quantity > 0 and not section_id:
            product = self.env['product.product'].browse(product_id)
            main_tmpl = product.product_tmpl_id.main_product_id
            if main_tmpl:
                # Look for an existing section line with this main product's name
                section = self.order_line.filtered(
                    lambda l: l.display_type == 'line_section'
                    and l.name == main_tmpl.name
                )[:1]
                if not section:
                    max_seq = max(self.order_line.mapped('sequence') or [0])
                    section = self.env['sale.order.line'].create({
                        'order_id': self.id,
                        'display_type': 'line_section',
                        'name': main_tmpl.name,
                        'sequence': max_seq + 1,
                    })
                section_id = section.id

        return super()._update_order_line_info(
            product_id, quantity, section_id=section_id, **kwargs
        )
