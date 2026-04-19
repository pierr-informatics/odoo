# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_proposal_notes = fields.Html(
        string='Executive Summary / Proposal Notes',
        help='Custom WYSIWYG notes injected into the PDF proposal by the salesperson.',
    )
