# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPricingComputation(TransactionCase):
    """Test cumulative tax-bracket-style pricing engine with margin-derived prices."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Tiers use transfer_price + margins; sale_price and mrp are computed.
        # margin_sale_to_transfer=40 → sale = transfer / 0.60
        # margin_mrp_to_sale=30     → mrp  = sale   / 0.70
        # Transfer prices chosen so sale_price is a clean round number:
        #   6000 → sale=10000,  4800 → sale=8000,  4200 → sale=7000,
        #   3600 → sale=6000,   3000 → sale=5000
        cls.product = cls.env['product.template'].create({
            'name': 'Ellider AI Suite',
            'type': 'service',
            'cpq_type': 'module',
            'list_price': 0.0,
            'pricing_tier_ids': [
                (0, 0, {
                    'sequence': 10,
                    'name': 'First 50 Beds',
                    'bracket_size': 50,
                    'transfer_price': 6000,
                    'margin_sale_to_transfer': 40,
                    'margin_mrp_to_sale': 30,
                }),
                (0, 0, {
                    'sequence': 20,
                    'name': 'Beds 51-100',
                    'bracket_size': 50,
                    'transfer_price': 4800,
                    'margin_sale_to_transfer': 40,
                    'margin_mrp_to_sale': 30,
                }),
                (0, 0, {
                    'sequence': 30,
                    'name': 'Beds 101-200',
                    'bracket_size': 100,
                    'transfer_price': 4200,
                    'margin_sale_to_transfer': 40,
                    'margin_mrp_to_sale': 30,
                }),
                (0, 0, {
                    'sequence': 40,
                    'name': 'Beds 201-300',
                    'bracket_size': 100,
                    'transfer_price': 3600,
                    'margin_sale_to_transfer': 40,
                    'margin_mrp_to_sale': 30,
                }),
                (0, 0, {
                    'sequence': 50,
                    'name': 'Beds 301+',
                    'bracket_size': 0,  # Unlimited
                    'transfer_price': 3000,
                    'margin_sale_to_transfer': 40,
                    'margin_mrp_to_sale': 30,
                }),
            ],
        })

        cls.partner = cls.env['res.partner'].create({'name': 'Test Hospital'})

    def _create_order_line(self, qty):
        """Helper: create an SO with one line for our product at given qty."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.product_variant_id.id,
            'product_uom_qty': qty,
        })
        return line

    # --- Derived price formula tests ---

    def test_computed_sale_price_from_margin(self):
        """sale_price = transfer / (1 - margin_st/100). 6000 / 0.60 = 10000."""
        tier = self.product.pricing_tier_ids.sorted('sequence')[0]
        self.assertAlmostEqual(tier.sale_price, 10000.0, places=2)

    def test_computed_mrp_from_margin(self):
        """mrp = sale / (1 - margin_ms/100). 10000 / 0.70 = 14285.71."""
        tier = self.product.pricing_tier_ids.sorted('sequence')[0]
        self.assertAlmostEqual(tier.mrp, 10000.0 / 0.70, places=2)

    # --- Cumulative sale total tests ---

    def test_186_beds_example(self):
        """186 beds: 50×10k + 50×8k + 86×7k = 1,502,000."""
        line = self._create_order_line(186)
        expected = (50 * 10000) + (50 * 8000) + (86 * 7000)  # 1502000
        self.assertAlmostEqual(line.computed_total_sale, expected, places=2)
        self.assertAlmostEqual(line.blended_avg_price, expected / 186, places=2)

    def test_single_tier_50_beds(self):
        """Exactly 50 beds fills only the first tier."""
        line = self._create_order_line(50)
        expected = 50 * 10000  # 500000
        self.assertAlmostEqual(line.computed_total_sale, expected, places=2)
        self.assertAlmostEqual(line.blended_avg_price, 10000.0, places=2)

    def test_boundary_100_beds(self):
        """100 beds fills tier 1 + tier 2 exactly."""
        line = self._create_order_line(100)
        expected = (50 * 10000) + (50 * 8000)  # 900000
        self.assertAlmostEqual(line.computed_total_sale, expected, places=2)

    def test_overflow_400_beds(self):
        """400 beds spans all 5 tiers including unlimited."""
        line = self._create_order_line(400)
        expected = (50 * 10000) + (50 * 8000) + (100 * 7000) + (100 * 6000) + (100 * 5000)
        self.assertAlmostEqual(line.computed_total_sale, expected, places=2)

    def test_zero_qty_no_crash(self):
        """Zero qty should produce zero totals, no division by zero."""
        line = self._create_order_line(0)
        self.assertAlmostEqual(line.computed_total_sale, 0.0, places=2)
        self.assertAlmostEqual(line.blended_avg_price, 0.0, places=2)

    def test_transfer_price_186_beds(self):
        """Verify transfer_price cumulative total for 186 beds."""
        line = self._create_order_line(186)
        expected = (50 * 6000) + (50 * 4800) + (86 * 4200)  # 901200
        self.assertAlmostEqual(line.computed_total_transfer_price, expected, places=2)

    def test_mrp_186_beds(self):
        """Verify MRP cumulative total for 186 beds using stored (rounded) mrp values."""
        tiers = self.product.pricing_tier_ids.sorted('sequence')
        t1_mrp, t2_mrp, t3_mrp = tiers[0].mrp, tiers[1].mrp, tiers[2].mrp
        expected = (50 * t1_mrp) + (50 * t2_mrp) + (86 * t3_mrp)
        line = self._create_order_line(186)
        self.assertAlmostEqual(line.computed_total_mrp, expected, places=2)

    def test_price_unit_is_blended_average(self):
        """price_unit on the SO line should equal the blended average."""
        line = self._create_order_line(186)
        expected_total = (50 * 10000) + (50 * 8000) + (86 * 7000)
        expected_avg = expected_total / 186
        self.assertAlmostEqual(line.price_unit, expected_avg, places=2)

    # --- Overflow beyond finite tiers ---

    def test_overflow_exceeds_finite_tiers(self):
        """600 beds: last tier (bracket_size=0) absorbs beds 301-600.
        sale total: 50×10k + 50×8k + 100×7k + 100×6k + 300×5k = 3,200,000
        """
        line = self._create_order_line(600)
        expected = (50 * 10000) + (50 * 8000) + (100 * 7000) + (100 * 6000) + (300 * 5000)
        self.assertAlmostEqual(line.computed_total_sale, expected, places=2)

    # --- MRP discount → quoted total ---

    def test_mrp_discount_quoted_total(self):
        """10% discount on Total List Price produces Quoted Total = MRP × 0.90."""
        line = self._create_order_line(186)
        mrp_total = line.computed_total_mrp
        line.write({'mrp_discount': 10.0})
        self.assertAlmostEqual(line.quoted_total, mrp_total * 0.90, places=2)
        self.assertAlmostEqual(line.quoted_price_per_bed, (mrp_total * 0.90) / 186, places=2)

    # --- ValidationError when quoted below dealer price ---

    def test_quoted_below_sale_price_raises(self):
        """A 99% discount brings quoted/bed far below dealer price → ValidationError."""
        from odoo.exceptions import ValidationError
        line = self._create_order_line(186)
        with self.assertRaises(ValidationError):
            line.write({'mrp_discount': 99.0})

