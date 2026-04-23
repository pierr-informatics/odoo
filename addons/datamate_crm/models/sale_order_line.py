# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    #=== CPQ Computed Fields ===#

    computed_total_sale = fields.Monetary(
        string='Total Dealer Price',
        compute='_compute_cpq_pricing',
        store=True,
        currency_field='currency_id',
    )
    computed_total_transfer_price = fields.Monetary(
        string='Total Base Cost',
        compute='_compute_cpq_pricing',
        store=True,
        currency_field='currency_id',
    )
    computed_total_mrp = fields.Monetary(
        string='Total List Price',
        compute='_compute_cpq_pricing',
        store=True,
        currency_field='currency_id',
    )
    blended_avg_price = fields.Float(
        string='Effective Price / Bed',
        compute='_compute_cpq_pricing',
        store=True,
        digits='Product Price',
    )

    #=== MRP Discount & Quoted Price Fields ===#

    mrp_discount = fields.Float(
        string='List Price Discount (%)',
        default=0.0,
        digits='Discount',
        help='Discount percentage applied to the Total List Price to arrive at the Quoted Total.',
    )
    quoted_total = fields.Monetary(
        string='Quoted Total',
        compute='_compute_cpq_pricing',
        store=True,
        currency_field='currency_id',
    )
    quoted_price_per_bed = fields.Float(
        string='Quoted Price / Bed',
        compute='_compute_cpq_pricing',
        store=True,
        digits='Product Price',
    )

    #=== Bracket Breakdown HTML (display only) ===#

    bracket_breakdown_html = fields.Html(
        string='Pricing Breakdown',
        compute='_compute_bracket_breakdown_html',
        sanitize=False,
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
        'product_id.pricing_tier_ids.transfer_price',
        'product_id.pricing_tier_ids.mrp',
        'product_id.pricing_tier_ids.margin_sale_to_transfer',
        'product_id.pricing_tier_ids.margin_mrp_to_sale',
        'mrp_discount',
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
                line.computed_total_transfer_price = 0.0
                line.computed_total_mrp = 0.0
                line.blended_avg_price = 0.0
                line.quoted_total = 0.0
                line.quoted_price_per_bed = 0.0
                continue

            totals = self._calculate_cumulative_totals(
                product.pricing_tier_ids.sorted('sequence'), qty,
            )

            line.computed_total_sale = totals['sale_price']
            line.computed_total_transfer_price = totals['transfer_price']
            line.computed_total_mrp = totals['mrp']
            line.blended_avg_price = totals['sale_price'] / qty

            discount = line.mrp_discount or 0.0
            qt = totals['mrp'] * (1.0 - discount / 100.0)
            line.quoted_total = qt
            line.quoted_price_per_bed = qt / qty

    @staticmethod
    def _calculate_cumulative_totals(tiers, qty):
        """Cumulative bracket-style calculation across all price types.

        Iterates sorted tiers, filling each bracket until qty is exhausted.
        If qty exceeds the sum of all finite bracket sizes, the last tier's
        prices are applied to the remaining beds (overflow behaviour).

        Returns dict with totals and a breakdown list for display.
        """
        remaining = qty
        totals = {
            'sale_price': 0.0,
            'transfer_price': 0.0,
            'mrp': 0.0,
            'breakdown': [],  # list of (from_bed, to_bed, mrp_per_bed, beds, mrp_total)
        }

        tiers_list = list(tiers)
        bed_cursor = 1

        for i, tier in enumerate(tiers_list):
            if remaining <= 0:
                break
            is_last = (i == len(tiers_list) - 1)
            # bracket_size 0 = unlimited; last tier absorbs overflow
            if tier.bracket_size <= 0 or is_last:
                beds_in_bracket = remaining
            else:
                beds_in_bracket = min(remaining, tier.bracket_size)

            totals['sale_price'] += beds_in_bracket * tier.sale_price
            totals['transfer_price'] += beds_in_bracket * tier.transfer_price
            totals['mrp'] += beds_in_bracket * tier.mrp

            totals['breakdown'].append((
                bed_cursor,
                bed_cursor + beds_in_bracket - 1,
                tier.mrp,
                beds_in_bracket,
                beds_in_bracket * tier.mrp,
            ))
            bed_cursor += beds_in_bracket
            remaining -= beds_in_bracket

        return totals

    #=== Breakdown HTML renderer ===#

    @api.depends(
        'product_id',
        'product_uom_qty',
        'product_id.cpq_type',
        'product_id.pricing_tier_ids',
        'product_id.pricing_tier_ids.sequence',
        'product_id.pricing_tier_ids.bracket_size',
        'product_id.pricing_tier_ids.mrp',
        'mrp_discount',
        'computed_total_mrp',
        'quoted_total',
        'quoted_price_per_bed',
        'blended_avg_price',
    )
    def _compute_bracket_breakdown_html(self):
        for line in self:
            product = line.product_id
            qty = line.product_uom_qty or 0.0

            if (
                not product
                or product.cpq_type != 'module'
                or not product.pricing_tier_ids
                or qty <= 0
            ):
                line.bracket_breakdown_html = ''
                continue

            totals = self._calculate_cumulative_totals(
                product.pricing_tier_ids.sorted('sequence'), qty,
            )

            currency = line.currency_id
            symbol = currency.symbol or ''
            position = currency.position  # 'before' or 'after'

            def fmt(val):
                s = '{:,.2f}'.format(val)
                return f'{symbol}\u00a0{s}' if position == 'before' else f'{s}\u00a0{symbol}'

            rows = ''
            for from_b, to_b, mrp_pb, beds, mrp_tot in totals['breakdown']:
                rows += (
                    f'<tr>'
                    f'<td class="text-end">{int(from_b)}</td>'
                    f'<td class="text-end">{int(to_b)}</td>'
                    f'<td class="text-end">{fmt(mrp_pb)}</td>'
                    f'<td class="text-end">{int(beds)}</td>'
                    f'<td class="text-end">{fmt(mrp_tot)}</td>'
                    f'</tr>'
                )

            discount = line.mrp_discount or 0.0
            discount_amount = line.computed_total_mrp - line.quoted_total

            html = f'''
<div style="font-family: Arial, sans-serif; font-size: 13px;">
  <table class="table table-sm table-bordered" style="max-width: 620px;">
    <thead class="table-light">
      <tr>
        <th colspan="5" style="background:#f0f4ff; color:#1a2e6e; font-size:14px; padding:8px;">
          Pricing Breakdown &mdash; {product.name}
          <span style="float:right; font-weight:normal; color:#555;">Total Beds: {int(qty)}</span>
        </th>
      </tr>
      <tr style="background:#e8edf8; color:#333;">
        <th class="text-end">From</th>
        <th class="text-end">To</th>
        <th class="text-end">List Price / Bed</th>
        <th class="text-end">Beds</th>
        <th class="text-end">List Total</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
    <tfoot>
      <tr>
        <td colspan="4" class="text-end fw-bold">Total List Price</td>
        <td class="text-end fw-bold">{fmt(line.computed_total_mrp)}</td>
      </tr>
      <tr>
        <td colspan="4" class="text-end text-muted">Discount ({discount:.1f}%)</td>
        <td class="text-end text-muted">- {fmt(discount_amount)}</td>
      </tr>
      <tr style="background:#f0f4ff;">
        <td colspan="4" class="text-end fw-bold" style="color:#1a2e6e;">Quoted Total</td>
        <td class="text-end fw-bold" style="color:#1a2e6e;">{fmt(line.quoted_total)}</td>
      </tr>
      <tr style="background:#f0f4ff;">
        <td colspan="4" class="text-end" style="color:#1a2e6e;">Quoted Price / Bed</td>
        <td class="text-end" style="color:#1a2e6e;">{fmt(line.quoted_price_per_bed)}</td>
      </tr>
      <tr>
        <td colspan="4" class="text-end text-muted" style="font-size:11px;">Effective Dealer Price / Bed</td>
        <td class="text-end text-muted" style="font-size:11px;">{fmt(line.blended_avg_price)}</td>
      </tr>
    </tfoot>
  </table>
</div>'''
            line.bracket_breakdown_html = html

    #=== Validation: cannot quote below dealer price ===#

    @api.constrains('mrp_discount', 'product_uom_qty', 'product_id')
    def _check_quoted_price_above_dealer(self):
        for line in self:
            product = line.product_id
            if (
                not product
                or product.cpq_type != 'module'
                or not product.pricing_tier_ids
                or (line.product_uom_qty or 0) <= 0
                or (line.mrp_discount or 0) <= 0
            ):
                continue
            if line.quoted_price_per_bed < line.blended_avg_price:
                raise ValidationError(
                    "You cannot quote below the sale price!\n"
                    f"Quoted Price / Bed ({line.quoted_price_per_bed:,.2f}) is below "
                    f"Dealer Price / Bed ({line.blended_avg_price:,.2f}) "
                    f"for product '{product.name}'."
                )

    #=== Override price_unit to inject blended average ===#

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_price_unit(self):
        super()._compute_price_unit()

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
