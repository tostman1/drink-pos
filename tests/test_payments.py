import unittest

from app.models.responses import CardPaymentBreakdown
from app.services import payments


class PaymentServiceTests(unittest.TestCase):
    def test_card_payment_fee_uses_minimum_for_small_amounts(self):
        self.assertEqual(payments.card_payment_fee_cents(100), 20)

    def test_card_payment_fee_rounds_percentage_up(self):
        self.assertEqual(payments.card_payment_fee_cents(2500), 75)
        self.assertEqual(payments.card_payment_fee_cents(2501), 76)

    def test_card_payment_breakdown_without_rounding(self):
        breakdown = payments.card_payment_breakdown(10)

        self.assertIsInstance(breakdown, CardPaymentBreakdown)
        self.assertEqual(breakdown.base_amount_cents, 1000)
        self.assertEqual(breakdown.card_fee_cents, 30)
        self.assertEqual(breakdown.amount_cents, 1030)
        self.assertEqual(breakdown.rounding_adjustment_cents, 0)

    def test_card_payment_breakdown_rounds_to_next_five(self):
        breakdown = payments.card_payment_breakdown(10, "five")

        self.assertEqual(breakdown.amount_cents, 1500)
        self.assertEqual(breakdown.rounding_adjustment_cents, 470)

    def test_invalid_rounding_mode_raises_payment_error(self):
        with self.assertRaises(payments.PaymentError):
            payments.card_payment_breakdown(10, "bad")


if __name__ == "__main__":
    unittest.main()
