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

    # === Manual inputs ===
    transfer_price = fields.Float(
        string='Transfer Price / Bed',
        digits='Product Price',
    )
    margin_sale_to_transfer = fields.Float(
        string='Sale→Transfer Margin (%)',
        default=40.0,
        help='Margin from Sale Price down to Transfer Price. '
             'E.g. 40 means Sale Price = Transfer / (1 - 0.40).',
    )
    margin_mrp_to_sale = fields.Float(
        string='MRP→Sale Margin (%)',
        default=30.0,
        help='Margin from MRP down to Sale Price. '
             'E.g. 30 means MRP = Sale Price / (1 - 0.30).',
    )

    # === Derived (read-only, computed & stored) ===
    sale_price = fields.Float(
        string='Sale Price / Bed',
        compute='_compute_derived_prices',
        store=True,
        digits='Product Price',
    )
    mrp = fields.Float(
        string='MRP / Bed',
        compute='_compute_derived_prices',
        store=True,
        digits='Product Price',
    )

    @api.depends('transfer_price', 'margin_sale_to_transfer', 'margin_mrp_to_sale')
    def _compute_derived_prices(self):
        for tier in self:
            m_st = tier.margin_sale_to_transfer / 100.0
            m_ms = tier.margin_mrp_to_sale / 100.0
            if m_st >= 1.0:
                sale = 0.0
            else:
                sale = tier.transfer_price / (1.0 - m_st)
            tier.sale_price = sale
            if m_ms >= 1.0:
                tier.mrp = 0.0
            else:
                tier.mrp = sale / (1.0 - m_ms)
