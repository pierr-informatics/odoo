# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cpq_type = fields.Selection(
        selection=[
            ('main_product', 'Main Product'),
            ('module', 'Module'),
        ],
        string='CPQ Type',
        help='Main Product: parent family shown as section header. Module: line item with tier pricing.',
    )
    main_product_id = fields.Many2one(
        comodel_name='product.template',
        string='Main Product',
        domain=[('cpq_type', '=', 'main_product')],
        help='Parent main product this module belongs to. Used to auto-group lines on quotes.',
    )
    pricing_tier_ids = fields.One2many(
        comodel_name='product.pricing.tier',
        inverse_name='product_tmpl_id',
        string='Pricing Tiers',
    )
    preset_proposal_notes = fields.Html(
        string='Proposal Feature Notes',
        help='Feature highlights printed on the PDF proposal for this module.',
    )
    preset_terms_conditions = fields.Html(
        string='Terms & Conditions',
        help='Legal/SLA terms printed on the PDF proposal for this module.',
    )
