# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPricingComputation(TransactionCase):
    """Test cumulative tax-bracket-style pricing engine."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a module product with Ellider AI Suite tiers
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
                    'sale_price': 10000,
                    'min_cutoff': 8500,
                    'mrp': 16000,
                    'transfer_price': 7692,
                }),
                (0, 0, {
                    'sequence': 20,
                    'name': 'Beds 51-100',
                    'bracket_size': 50,
                    'sale_price': 8000,
                    'min_cutoff': 6800,
                    'mrp': 12800,
                    'transfer_price': 6154,
                }),
                (0, 0, {
                    'sequence': 30,
                    'name': 'Beds 101-200',
                    'bracket_size': 100,
                    'sale_price': 7000,
                    'min_cutoff': 5950,
                    'mrp': 11200,
                    'transfer_price': 5385,
                }),
                (0, 0, {
                    'sequence': 40,
                    'name': 'Beds 201-300',
                    'bracket_size': 100,
                    'sale_price': 6000,
                    'min_cutoff': 5100,
                    'mrp': 9600,
                    'transfer_price': 4615,
                }),
                (0, 0, {
                    'sequence': 50,
                    'name': 'Beds 301+',
                    'bracket_size': 0,  # Unlimited
                    'sale_price': 5000,
                    'min_cutoff': 4250,
                    'mrp': 8000,
                    'transfer_price': 3846,
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

    def test_186_beds_example(self):
        """186 beds: 50×10k + 50×8k + 86×7k = 15,02,000."""
        line = self._create_order_line(186)
        expected = (50 * 10000) + (50 * 8000) + (86 * 7000)  # 1502000
        self.assertAlmostEqual(line.computed_total_sale, expected, places=2)
        self.assertAlmostEqual(line.blended_avg_price, expected / 186, places=2)

    def test_single_tier_50_beds(self):
        """Exactly 50 beds fills only the first tier."""
        line = self._create_order_line(50)
        expected = 50 * 10000  # 500000
        self.assertAlmostEqual(line.computed_total_sale, expected, places=2)
        self.assertAlmostEqual(line.blended_avg_price, 10000, places=2)

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

    def test_min_cutoff_186_beds(self):
        """Verify min_cutoff cumulative total for 186 beds."""
        line = self._create_order_line(186)
        expected = (50 * 8500) + (50 * 6800) + (86 * 5950)
        self.assertAlmostEqual(line.computed_total_min_cutoff, expected, places=2)

    def test_transfer_price_186_beds(self):
        """Verify transfer_price cumulative total for 186 beds."""
        line = self._create_order_line(186)
        expected = (50 * 7692) + (50 * 6154) + (86 * 5385)
        self.assertAlmostEqual(line.computed_total_transfer_price, expected, places=2)

    def test_mrp_186_beds(self):
        """Verify MRP cumulative total for 186 beds."""
        line = self._create_order_line(186)
        expected = (50 * 16000) + (50 * 12800) + (86 * 11200)
        self.assertAlmostEqual(line.computed_total_mrp, expected, places=2)

    def test_price_unit_is_blended_average(self):
        """price_unit on the SO line should be the blended average."""
        line = self._create_order_line(186)
        expected_total = (50 * 10000) + (50 * 8000) + (86 * 7000)
        expected_avg = expected_total / 186
        self.assertAlmostEqual(line.price_unit, expected_avg, places=2)
