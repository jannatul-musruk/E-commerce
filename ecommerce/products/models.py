from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify


class CustomUser(AbstractUser):
    """Our own user model.

    AbstractUser already gives us username, first_name, last_name, email and a
    securely hashed password, plus login/logout, permissions and admin support.
    We only add what Django does not have.
    """

    middle_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p) or self.username

    def __str__(self):
        return f"{self.username} ({self.full_name})"


class Customer(models.Model):
    """Shopping profile attached to a user. Created automatically on signup."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer"
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.full_name


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        Customer.objects.create(user=instance)


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('product_list')}?category={self.slug}"

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    origin = models.CharField(max_length=120, blank=True, help_text="Where the maker is based")

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    image = models.ImageField(upload_to="products/", blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])

    @property
    def starting_price(self):
        prices = [v.price for v in self.variants.all()]
        return min(prices) if prices else None

    @property
    def compare_at_price(self):
        cheapest = min(self.variants.all(), key=lambda v: v.price, default=None)
        return cheapest.compare_at_price if cheapest else None

    @property
    def discount_percent(self):
        cheapest = min(self.variants.all(), key=lambda v: v.price, default=None)
        return cheapest.discount_percent if cheapest else 0

    @property
    def total_stock(self):
        return sum(v.stock for v in self.variants.all())

    @property
    def in_stock(self):
        return self.total_stock > 0

    @property
    def average_rating(self):
        ratings = [r.rating for r in self.reviews.all()]
        if not ratings:
            return None
        return round(sum(ratings) / len(ratings), 1)

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    """A buyable version of a product, e.g. a size or a colour."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=120, help_text="e.g. Indigo / Medium")
    sku = models.CharField(max_length=40, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The old price. Leave empty if this item is not on offer.",
    )
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["price"]
        unique_together = ("product", "name")

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def is_on_offer(self):
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def discount_percent(self):
        if not self.is_on_offer:
            return 0
        saved = self.compare_at_price - self.price
        return int(round(saved / self.compare_at_price * 100))

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class Cart(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    def clear(self):
        self.items.all().delete()

    def __str__(self):
        return f"Cart of {self.customer}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "variant")
        ordering = ["added_at"]

    @property
    def line_total(self):
        return self.variant.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.variant.name}"


class Order(models.Model):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (SHIPPED, "Shipped"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
    ]

    code = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"NK-{self.pk:05d}"
            super().save(update_fields=["code"])

    def get_absolute_url(self):
        return reverse("order_detail", args=[self.pk])

    @property
    def can_be_cancelled(self):
        return self.status in (self.PENDING, self.CONFIRMED)

    def __str__(self):
        return f"{self.code} — {self.customer} — {self.get_status_display()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Price at the time of ordering"
    )

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.order.code} — {self.variant.name} x {self.quantity}"


class Payment(models.Model):
    CASH = "cash"
    BKASH = "bkash"
    NAGAD = "nagad"
    CARD = "card"
    METHOD_CHOICES = [
        (CASH, "Cash on delivery"),
        (BKASH, "bKash"),
        (NAGAD, "Nagad"),
        (CARD, "Card"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=CASH)
    transaction_id = models.CharField(max_length=60, blank=True)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        state = "paid" if self.is_paid else "unpaid"
        return f"{self.order.code} — {self.get_method_display()} — {state}"


class ShippingAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="shipping_address")
    recipient_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Bangladesh")

    class Meta:
        verbose_name_plural = "shipping addresses"

    def __str__(self):
        return f"{self.recipient_name}, {self.city}"


class Wishlist(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "product")
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.customer} saved {self.product.name}"


class Review(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "product")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} — {self.rating}/5 by {self.customer}"


class ReturnRequest(models.Model):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (REQUESTED, "Requested"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    order_item = models.OneToOneField(
        OrderItem, on_delete=models.CASCADE, related_name="return_request"
    )
    reason = models.TextField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=REQUESTED)
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return for {self.order_item} — {self.get_status_display()}"


class Subscription(models.Model):
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="subscription"
    )
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        state = "active" if self.is_active else "paused"
        return f"{self.customer} — newsletter {state}"


class Notification(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer} — {self.message[:40]}"


class ActivityLog(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity",
    )
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.customer or "guest"
        return f"{who} — {self.action} — {self.created_at:%d %b %Y %H:%M}"
