"""Fill an empty database with a believable shop.

    python manage.py seed_data          # add sample data
    python manage.py seed_data --fresh  # wipe shop data first, then add
"""

import random
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from products.models import (
    ActivityLog,
    Brand,
    Cart,
    Category,
    CustomUser,
    Notification,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
    Review,
    ShippingAddress,
    Subscription,
    Wishlist,
)

PALETTE = ["#e2402b", "#b82f1e", "#ffb020", "#1f8a4c", "#2b1a14", "#f0e6e0"]

CATALOGUE = [
    {
        "category": ("Pottery", "Thrown and fired in Rayer Bazar"),
        "brand": ("Rayer Bazar Clay", "Dhaka"),
        "products": [
            ("Terracotta water jug", "A tall unglazed jug that keeps water cool through the afternoon. Thrown on a kick wheel and fired in a wood kiln, so no two are the same shade.", [("Medium", 950, 12), ("Large", 1450, 7)]),
            ("Stoneware dinner plate", "A heavy plate with a dark rim, glazed inside only. Stacks well and takes daily washing without chipping.", [("Set of two", 1200, 15), ("Set of six", 3300, 4)]),
        ],
    },
    {
        "category": ("Jamdani & textiles", "Handloom from Rupganj and Tangail"),
        "brand": ("Rupganj Handloom", "Narayanganj"),
        "products": [
            ("Half-silk jamdani saree", "Six yards woven on a pit loom over roughly two months. The motif is the classic panna hazar, picked by hand thread by thread.", [("Indigo", 14500, 3), ("Off white", 13800, 2)]),
            ("Cotton gamcha, pair", "The everyday checked towel, woven loose so it dries fast. Softens with every wash.", [("Red check", 420, 40), ("Green check", 420, 26)]),
            ("Nokshi kantha throw", "Old cotton saris layered and quilted with running stitch. This one carries a lotus and fish motif across the centre.", [("Single", 5200, 5), ("Double", 8900, 2)]),
        ],
    },
    {
        "category": ("Jute & cane", "Woven goods from Faridpur"),
        "brand": ("Faridpur Jute Works", "Faridpur"),
        "products": [
            ("Jute market bag", "Wide enough for a week of vegetables, with cotton webbing handles stitched through the base so nothing tears out.", [("Natural", 680, 30), ("Dyed indigo", 760, 18)]),
            ("Cane floor basket", "Storage for blankets or toys, woven over a bamboo frame. Holds its shape when empty.", [("Small", 1100, 14), ("Tall", 1850, 6)]),
        ],
    },
    {
        "category": ("Leather", "Vegetable-tanned in Savar"),
        "brand": ("Savar Tannery Goods", "Savar"),
        "products": [
            ("Card wallet", "Four pockets, no lining, one piece of hide folded and saddle stitched. It darkens where you handle it.", [("Tan", 1650, 20), ("Black", 1650, 11)]),
            ("Satchel bag", "Fits a 14 inch laptop with a notebook beside it. Solid brass buckles that can be replaced rather than binned.", [("Tan", 7800, 4), ("Dark brown", 8200, 3)]),
        ],
    },
    {
        "category": ("Brass & metal", "Cast by hand in Dhamrai"),
        "brand": ("Dhamrai Metal", "Dhamrai"),
        "products": [
            ("Brass oil lamp", "Cast by the lost wax method, the way the workshop has done it for four generations. Comes unlacquered so it ages.", [("Small", 2400, 9), ("Pair", 4500, 5)]),
            ("Copper water pot", "Two litres, tin lined inside. Traditionally used to store drinking water overnight.", [("Two litre", 3100, 6)]),
        ],
    },
]

REVIEW_TEXT = [
    (5, "Arrived in three days and packed properly. The colour is closer to the photo than I expected."),
    (4, "Good work and clearly handmade. One edge is slightly uneven, which I do not mind at all."),
    (5, "Bought a second one as a wedding gift. Worth the price for the craft."),
    (3, "Nice piece, but the delivery took longer than promised in my area."),
    (4, "Solid and heavier than it looks. Happy with it."),
]


def make_image(seed_text, base_colour):
    """Draw a simple woven-looking pattern so the shop is not full of empty boxes."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    rng = random.Random(seed_text)
    width, height = 800, 1000
    image = Image.new("RGB", (width, height), "#edeee7")
    draw = ImageDraw.Draw(image)

    draw.rectangle([60, 60, width - 60, height - 60], fill=base_colour)

    accent = rng.choice([c for c in PALETTE if c != base_colour])
    step = rng.choice([40, 55, 70])
    style = rng.choice(["stripes", "diamonds", "dots"])

    if style == "stripes":
        for y in range(90, height - 90, step):
            draw.line([(90, y), (width - 90, y)], fill=accent, width=rng.choice([3, 5, 8]))
    elif style == "diamonds":
        for y in range(120, height - 120, step * 2):
            for x in range(120, width - 120, step * 2):
                size = step - 10
                draw.polygon(
                    [(x, y - size), (x + size, y), (x, y + size), (x - size, y)],
                    outline=accent,
                    width=4,
                )
    else:
        for y in range(120, height - 120, step):
            for x in range(120, width - 120, step):
                r = step // 5
                draw.ellipse([x - r, y - r, x + r, y + r], fill=accent)

    draw.rectangle([60, 60, width - 60, height - 60], outline="#14203c", width=6)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Load sample categories, products, users, orders and reviews."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing shop data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["fresh"]:
            for model in (
                ActivityLog, Notification, Subscription, Wishlist, Review,
                OrderItem, ShippingAddress, Payment, Order, Cart,
                ProductVariant, Product, Brand, Category,
            ):
                model.objects.all().delete()
            CustomUser.objects.filter(is_superuser=False).delete()
            self.stdout.write("Cleared existing shop data.")

        if Product.objects.exists():
            self.stdout.write(
                self.style.WARNING("Products already exist. Use --fresh to rebuild.")
            )
            return

        rng = random.Random(7)
        sku_counter = 1

        for block in CATALOGUE:
            category = Category.objects.create(
                name=block["category"][0], description=block["category"][1]
            )
            category_image = make_image(block["category"][0], rng.choice(PALETTE[:4]))
            if category_image:
                category.image.save(f"{category.slug}.jpg", category_image, save=True)
            brand = Brand.objects.create(
                name=block["brand"][0], origin=block["brand"][1]
            )
            for name, description, variants in block["products"]:
                product = Product.objects.create(
                    name=name,
                    description=description,
                    category=category,
                    brand=brand,
                    is_featured=rng.random() < 0.45,
                )
                image = make_image(name, rng.choice(PALETTE[:4]))
                if image:
                    product.image.save(f"{product.slug}.jpg", image, save=True)

                for variant_name, price, stock in variants:
                    # Put roughly a third of the range on offer.
                    compare_at = None
                    if rng.random() < 0.38:
                        markup = rng.choice([1.15, 1.2, 1.25, 1.3])
                        compare_at = Decimal(int(price * markup))
                    ProductVariant.objects.create(
                        product=product,
                        name=variant_name,
                        sku=f"NK-{sku_counter:04d}",
                        price=Decimal(price),
                        compare_at_price=compare_at,
                        stock=stock,
                    )
                    sku_counter += 1

        # --- people ---------------------------------------------------
        if not CustomUser.objects.filter(username="admin").exists():
            CustomUser.objects.create_superuser(
                username="admin",
                email="admin@nokshi.test",
                password="admin1234",
                first_name="Shop",
                last_name="Manager",
            )

        shoppers = [
            ("rumi", "Rumi", "Ahmed", "rumi@example.com", "01712345678", "Dhaka"),
            ("nabila", "Nabila", "Haque", "nabila@example.com", "01812345678", "Chattogram"),
            ("tanvir", "Tanvir", "Islam", "tanvir@example.com", "01912345678", "Dhaka"),
        ]
        customers = []
        for username, first, last, email, phone, city in shoppers:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password="nokshi1234",
                first_name=first,
                last_name=last,
            )
            customer = user.customer
            customer.phone = phone
            customer.city = city
            customer.address = f"House {rng.randint(2, 90)}, Road {rng.randint(1, 30)}"
            customer.save()
            Subscription.objects.create(customer=customer, is_active=rng.random() < 0.7)
            customers.append(customer)

        products = list(Product.objects.prefetch_related("variants"))

        # --- reviews, wishlists, orders -------------------------------
        for customer in customers:
            for product in rng.sample(products, 4):
                rating, comment = rng.choice(REVIEW_TEXT)
                Review.objects.get_or_create(
                    customer=customer,
                    product=product,
                    defaults={"rating": rating, "comment": comment},
                )
            for product in rng.sample(products, 2):
                Wishlist.objects.get_or_create(customer=customer, product=product)

        statuses = [Order.DELIVERED, Order.SHIPPED, Order.CONFIRMED, Order.PENDING]
        for index, customer in enumerate(customers):
            for _ in range(rng.randint(1, 2)):
                chosen = rng.sample(products, rng.randint(1, 3))
                order = Order.objects.create(customer=customer, status=rng.choice(statuses))
                subtotal = Decimal("0.00")
                for product in chosen:
                    variant = rng.choice(list(product.variants.all()))
                    quantity = rng.randint(1, 2)
                    OrderItem.objects.create(
                        order=order,
                        variant=variant,
                        quantity=quantity,
                        unit_price=variant.price,
                    )
                    subtotal += variant.price * quantity

                delivery = Decimal(60 if customer.city == "Dhaka" else 120)
                order.subtotal = subtotal
                order.delivery_charge = delivery
                order.total = subtotal + delivery
                order.save()

                ShippingAddress.objects.create(
                    order=order,
                    recipient_name=customer.user.full_name,
                    phone=customer.phone,
                    address=customer.address,
                    city=customer.city,
                    postal_code=rng.choice(["1205", "1209", "4000", "1230"]),
                )
                method = rng.choice([Payment.CASH, Payment.BKASH, Payment.NAGAD, Payment.CARD])
                paid = method != Payment.CASH or order.status == Order.DELIVERED
                Payment.objects.create(
                    order=order,
                    amount=order.total,
                    method=method,
                    is_paid=paid,
                    paid_at=timezone.now() if paid else None,
                    transaction_id=f"TRX{rng.randint(100000, 999999)}" if method != Payment.CASH else "",
                )
                Notification.objects.create(
                    customer=customer,
                    message=f"Order {order.code} is {order.get_status_display().lower()}.",
                    link=order.get_absolute_url(),
                    is_read=index != 0,
                )
                ActivityLog.objects.create(customer=customer, action=f"Placed order {order.code}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {Product.objects.count()} products, "
                f"{Order.objects.count()} orders and {CustomUser.objects.count()} users.\n"
                "Log in as admin / admin1234 or rumi / nokshi1234."
            )
        )
