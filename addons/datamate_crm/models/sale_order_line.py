# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    #=== CPQ Computed Fields ===#

    computed_total_sale = fields.Monetary(
        string='CPQ Total (Sale)',
        compute='_compute_cpq_pricing',
        store=True,
        currency_field='currency_id',
    )
    computed_total_min_cutoff = fields.Monetary(
        string='CPQ Total (Min Cutoff)',
        compute='_compute_cpq_pricing',
        store=True,
        currency_field='currency_id',
    )
    computed_total_transfer_price = fields.Monetary(
        string='CPQ Total (Transfer)',
        compute='_compute_cpq_pricing',
        store=True,
        currency_field='currency_id',
    )
    computed_total_mrp = fields.Monetary(
        string='CPQ Total (MRP)',
        compute='_compute_cpq_pricing',
        store=True,
        currency_field='currency_id',
    )
    blended_avg_price = fields.Float(
        string='Blended Avg Price',
        compute='_compute_cpq_pricing',
        store=True,
        digits='Product Price',
    )

    #=== CPQ Pricing Engine ===#

    @api.depends(
        'product_id',
        'product_uom_qty',
        'product_id.cpq_type',
        'product_id.pricing_tier_ids',
        'product_id.pricing_tier_ids.sequence',
        'product_id.pricing_tier_ids.bracket_size',
        'product_id.pricing_tier_ids.sale_price',
        'product_id.pricing_tier_ids.min_cutoff',
        'product_id.pricing_tier_ids.transfer_price',
        'product_id.pricing_tier_ids.mrp',
    )
    def _compute_cpq_pricing(self):
        for line in self:
            product = line.product_id
            qty = line.product_uom_qty or 0.0

            if (
                not product
                or product.cpq_type != 'module'
                or not product.pricing_tier_ids
                or qty <= 0
            ):
                line.computed_total_sale = 0.0
                line.computed_total_min_cutoff = 0.0
                line.computed_total_transfer_price = 0.0
                line.computed_total_mrp = 0.0
                line.blended_avg_price = 0.0
                continue

            totals = self._calculate_cumulative_totals(
                product.pricing_tier_ids.sorted('sequence'), qty,
            )

            line.computed_total_sale = totals['sale_price']
            line.computed_total_min_cutoff = totals['min_cutoff']
            line.computed_total_transfer_price = totals['transfer_price']
            line.computed_total_mrp = totals['mrp']
            line.blended_avg_price = totals['sale_price'] / qty

    @staticmethod
    def _calculate_cumulative_totals(tiers, qty):
        """Cumulative tax-bracket-style calculation across all price types.

        Iterates sorted tiers, filling each bracket until qty is exhausted.
        bracket_size == 0 means unlimited (absorbs all remaining qty).

        Returns dict with total for each price type.
        """
        remaining = qty
        totals = {
            'sale_price': 0.0,
            'min_cutoff': 0.0,
            'transfer_price': 0.0,
            'mrp': 0.0,
        }

        for tier in tiers:
            if remaining <= 0:
                break
            # bracket_size 0 = unlimited
            if tier.bracket_size <= 0:
                beds_in_bracket = remaining
            else:
                beds_in_bracket = min(remaining, tier.bracket_size)

            totals['sale_price'] += beds_in_bracket * tier.sale_price
            totals['min_cutoff'] += beds_in_bracket * tier.min_cutoff
            totals['transfer_price'] += beds_in_bracket * tier.transfer_price
            totals['mrp'] += beds_in_bracket * tier.mrp

            remaining -= beds_in_bracket

        return totals

    #=== Override price_unit to inject blended average ===#

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_price_unit(self):
        # Let Odoo compute the standard price first
        super()._compute_price_unit()

        # Now override with CPQ blended average where applicable
        for line in self:
            product = line.product_id
            if (
                not product
                or product.cpq_type != 'module'
                or not product.pricing_tier_ids
                or (line.product_uom_qty or 0) <= 0
            ):
                continue

            blended = line.blended_avg_price
            if blended:
                line.update({
                    'price_unit': blended,
                    'technical_price_unit': blended,
                })
