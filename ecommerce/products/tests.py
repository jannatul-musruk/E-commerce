from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Brand, Cart, CartItem, Category, CustomUser, Product, ProductVariant


class ShopFlowTests(TestCase):
    """Enough coverage to prove the main purchase path works."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='rumi', email='rumi@example.com', password='nokshi-pass-123'
        )
        category = Category.objects.create(name='Pottery')
        brand = Brand.objects.create(name='Rayer Bazar Clay')
        self.product = Product.objects.create(
            name='Terracotta water jug',
            description='Hand-thrown jug.',
            category=category,
            brand=brand,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, name='Large', sku='JUG-L', price=Decimal('1450.00'), stock=5
        )

    def test_customer_profile_created_with_user(self):
        self.assertTrue(hasattr(self.user, 'customer'))

    def test_password_is_hashed(self):
        self.assertNotEqual(self.user.password, 'nokshi-pass-123')
        self.assertTrue(self.user.check_password('nokshi-pass-123'))

    def test_product_page_loads(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Terracotta water jug')

    def test_cart_requires_login(self):
        response = self.client.get(reverse('cart_detail'))
        self.assertEqual(response.status_code, 302)

    def test_add_to_bag_and_checkout(self):
        self.client.login(username='rumi', password='nokshi-pass-123')
        self.client.post(reverse('cart_add', args=[self.variant.pk]), {'quantity': 2})
        cart = Cart.objects.get(customer=self.user.customer)
        self.assertEqual(cart.item_count, 2)
        self.assertEqual(cart.subtotal, Decimal('2900.00'))

        response = self.client.post(
            reverse('checkout'),
            {
                'recipient_name': 'Rumi Ahmed',
                'phone': '01712345678',
                'address': '12 Dhanmondi',
                'city': 'Dhaka',
                'postal_code': '1209',
                'country': 'Bangladesh',
                'payment_method': 'bkash',
            },
        )
        self.assertEqual(response.status_code, 302)
        order = self.user.customer.orders.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.total, Decimal('2960.00'))  # 2900 + 60 delivery
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)  # stock went down
        self.assertEqual(CartItem.objects.count(), 0)  # bag cleared

    def test_cannot_add_more_than_stock(self):
        self.client.login(username='rumi', password='nokshi-pass-123')
        self.client.post(reverse('cart_add', args=[self.variant.pk]), {'quantity': 99})
        self.assertEqual(CartItem.objects.count(), 0)
