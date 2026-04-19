# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductPricingTier(models.Model):
    _name = 'product.pricing.tier'
    _description = 'Product Pricing Tier'
    _order = 'sequence, id'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Bracket Name', required=True)
    bracket_size = fields.Integer(
        string='Bracket Size',
        help='Number of beds in this bracket. Set 0 for unlimited (remaining beds).',
    )
    sale_price = fields.Float(string='Sale Price / Bed', digits='Product Price')
    min_cutoff = fields.Float(string='Min Cutoff / Bed', digits='Product Price')
    mrp = fields.Float(string='MRP / Bed', digits='Product Price')
    transfer_price = fields.Float(string='Transfer Price / Bed', digits='Product Price')
