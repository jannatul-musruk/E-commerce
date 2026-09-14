from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CheckoutForm,
    ProfileForm,
    ReturnRequestForm,
    ReviewForm,
    SignupForm,
)
from .models import (
    ActivityLog,
    Brand,
    Cart,
    CartItem,
    Category,
    Notification,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
    Review,
    Subscription,
    Wishlist,
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def get_cart(request):
    """Return the logged-in customer's cart, creating it on first use."""
    cart, _ = Cart.objects.get_or_create(customer=request.user.customer)
    return cart


def log(request, action):
    customer = getattr(request.user, "customer", None) if request.user.is_authenticated else None
    ActivityLog.objects.create(customer=customer, action=action)


def notify(customer, message, link=""):
    Notification.objects.create(customer=customer, message=message, link=link)


# --------------------------------------------------------------------------
# storefront
# --------------------------------------------------------------------------

def home(request):
    featured = (
        Product.objects.filter(is_active=True, is_featured=True)
        .select_related("category", "brand")
        .prefetch_related("variants", "reviews")[:6]
    )
    latest = (
        Product.objects.filter(is_active=True)
        .select_related("category", "brand")
        .prefetch_related("variants", "reviews")[:8]
    )
    categories = Category.objects.annotate(product_count=Count("products"))
    on_offer = [
        p
        for p in Product.objects.filter(is_active=True)
        .select_related("category", "brand")
        .prefetch_related("variants", "reviews")
        if p.discount_percent
    ][:5]
    hero_product = next((p for p in on_offer if p.image), None) or next(
        (p for p in latest if p.image), None
    )
    return render(
        request,
        "products/home.html",
        {
            "featured": featured,
            "latest": latest,
            "categories": categories,
            "on_offer": on_offer,
            "hero_product": hero_product,
        },
    )


def product_list(request):
    products = (
        Product.objects.filter(is_active=True)
        .select_related("category", "brand")
        .prefetch_related("variants", "reviews")
    )

    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "")
    brand_slug = request.GET.get("brand", "")
    sort = request.GET.get("sort", "new")

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(brand__name__icontains=query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)

    if sort == "price_low":
        products = products.order_by("variants__price")
    elif sort == "price_high":
        products = products.order_by("-variants__price")
    elif sort == "name":
        products = products.order_by("name")
    else:
        products = products.order_by("-created_at")
    products = products.distinct()

    paginator = Paginator(products, 9)
    page = paginator.get_page(request.GET.get("page"))

    querystring = request.GET.copy()
    querystring.pop("page", None)

    return render(
        request,
        "products/product_list.html",
        {
            "page": page,
            "categories": Category.objects.all(),
            "brands": Brand.objects.all(),
            "query": query,
            "category_slug": category_slug,
            "brand_slug": brand_slug,
            "sort": sort,
            "querystring": querystring.urlencode(),
            "result_count": paginator.count,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category", "brand").prefetch_related(
            "variants", "reviews__customer__user"
        ),
        slug=slug,
        is_active=True,
    )
    related = (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(pk=product.pk)
        .prefetch_related("variants")[:3]
    )

    already_reviewed = False
    in_wishlist = False
    if request.user.is_authenticated:
        customer = request.user.customer
        already_reviewed = Review.objects.filter(customer=customer, product=product).exists()
        in_wishlist = Wishlist.objects.filter(customer=customer, product=product).exists()

    return render(
        request,
        "products/product_detail.html",
        {
            "product": product,
            "related": related,
            "review_form": ReviewForm(),
            "already_reviewed": already_reviewed,
            "in_wishlist": in_wishlist,
        },
    )


@login_required
@require_POST
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug)
    customer = request.user.customer
    if Review.objects.filter(customer=customer, product=product).exists():
        messages.info(request, "You have already reviewed this product.")
        return redirect(product)

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.customer = customer
        review.product = product
        review.save()
        log(request, f"Reviewed {product.name}")
        messages.success(request, "Your review is live. Thanks for writing it.")
    else:
        messages.error(request, "Pick a rating and write a short comment.")
    return redirect(product)


# --------------------------------------------------------------------------
# cart
# --------------------------------------------------------------------------

@login_required
def cart_detail(request):
    cart = get_cart(request)
    items = cart.items.select_related("variant__product")
    return render(request, "products/cart.html", {"cart": cart, "items": items})


@login_required
@require_POST
def cart_add(request, variant_id):
    variant = get_object_or_404(ProductVariant, pk=variant_id)
    quantity = max(1, int(request.POST.get("quantity", 1)))
    cart = get_cart(request)

    item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
    new_quantity = quantity if created else item.quantity + quantity

    if new_quantity > variant.stock:
        messages.error(
            request,
            f"Only {variant.stock} left of {variant.name}. Adjust the quantity and try again.",
        )
        if created:
            item.delete()
        return redirect(variant.product)

    item.quantity = new_quantity
    item.save()
    log(request, f"Added {variant} to cart")
    messages.success(request, f"{variant.product.name} is in your bag.")
    return redirect("cart_detail")


@login_required
@require_POST
def cart_update(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__customer=request.user.customer)
    quantity = int(request.POST.get("quantity", 1))

    if quantity < 1:
        item.delete()
        messages.info(request, "Item removed.")
    elif quantity > item.variant.stock:
        messages.error(request, f"Only {item.variant.stock} left in stock.")
    else:
        item.quantity = quantity
        item.save()
        messages.success(request, "Bag updated.")
    return redirect("cart_detail")


@login_required
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__customer=request.user.customer)
    name = item.variant.product.name
    item.delete()
    messages.info(request, f"{name} removed from your bag.")
    return redirect("cart_detail")


# --------------------------------------------------------------------------
# wishlist
# --------------------------------------------------------------------------

@login_required
def wishlist_view(request):
    saved = (
        Wishlist.objects.filter(customer=request.user.customer)
        .select_related("product__brand")
        .prefetch_related("product__variants")
    )
    return render(request, "products/wishlist.html", {"saved": saved})


@login_required
@require_POST
def wishlist_toggle(request, slug):
    product = get_object_or_404(Product, slug=slug)
    entry = Wishlist.objects.filter(customer=request.user.customer, product=product).first()
    if entry:
        entry.delete()
        messages.info(request, f"{product.name} removed from your saved list.")
    else:
        Wishlist.objects.create(customer=request.user.customer, product=product)
        log(request, f"Saved {product.name}")
        messages.success(request, f"{product.name} saved for later.")
    return redirect(request.POST.get("next") or product.get_absolute_url())


# --------------------------------------------------------------------------
# checkout and orders
# --------------------------------------------------------------------------

@login_required
def checkout(request):
    cart = get_cart(request)
    items = list(cart.items.select_related("variant__product"))
    if not items:
        messages.info(request, "Your bag is empty. Add something first.")
        return redirect("product_list")

    customer = request.user.customer
    initial = {
        "recipient_name": request.user.full_name,
        "phone": customer.phone,
        "address": customer.address,
        "city": customer.city or "Dhaka",
    }
    form = CheckoutForm(request.POST or None, initial=initial)

    subtotal = cart.subtotal
    city_guess = (request.POST.get("city") or customer.city or "Dhaka").strip().lower()
    delivery = Decimal(
        settings.DELIVERY_CHARGE_INSIDE_DHAKA
        if city_guess == "dhaka"
        else settings.DELIVERY_CHARGE_OUTSIDE_DHAKA
    )

    if request.method == "POST" and form.is_valid():
        # Stock check before we touch anything
        short = [i for i in items if i.quantity > i.variant.stock]
        if short:
            messages.error(
                request,
                f"{short[0].variant.product.name} does not have enough stock left.",
            )
            return redirect("cart_detail")

        with transaction.atomic():
            delivery_charge = Decimal(
                settings.DELIVERY_CHARGE_INSIDE_DHAKA
                if form.cleaned_data["city"].strip().lower() == "dhaka"
                else settings.DELIVERY_CHARGE_OUTSIDE_DHAKA
            )
            order = Order.objects.create(
                customer=customer,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                total=subtotal + delivery_charge,
            )
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    unit_price=item.variant.price,
                )
                variant = item.variant
                variant.stock -= item.quantity
                variant.save(update_fields=["stock"])

            shipping = form.save(commit=False)
            shipping.order = order
            shipping.save()

            method = form.cleaned_data["payment_method"]
            Payment.objects.create(
                order=order,
                amount=order.total,
                method=method,
                is_paid=method != Payment.CASH,
                paid_at=timezone.now() if method != Payment.CASH else None,
            )
            cart.clear()

        notify(customer, f"Order {order.code} placed. We will confirm it shortly.", order.get_absolute_url())
        log(request, f"Placed order {order.code}")
        messages.success(request, f"Order {order.code} placed.")
        return redirect("order_detail", pk=order.pk)

    return render(
        request,
        "products/checkout.html",
        {
            "form": form,
            "items": items,
            "subtotal": subtotal,
            "delivery": delivery,
            "total": subtotal + delivery,
        },
    )


@login_required
def order_list(request):
    orders = (
        Order.objects.filter(customer=request.user.customer)
        .prefetch_related("items__variant__product")
        .select_related("payment")
    )
    return render(request, "products/order_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("payment", "shipping_address").prefetch_related(
            "items__variant__product", "items__return_request"
        ),
        pk=pk,
        customer=request.user.customer,
    )
    return render(
        request,
        "products/order_detail.html",
        {"order": order, "return_form": ReturnRequestForm()},
    )


@login_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user.customer)
    if not order.can_be_cancelled:
        messages.error(request, f"Order {order.code} is already {order.get_status_display().lower()}.")
        return redirect(order)

    with transaction.atomic():
        for item in order.items.select_related("variant"):
            variant = item.variant
            variant.stock += item.quantity
            variant.save(update_fields=["stock"])
        order.status = Order.CANCELLED
        order.save(update_fields=["status"])

    notify(request.user.customer, f"Order {order.code} was cancelled.", order.get_absolute_url())
    log(request, f"Cancelled order {order.code}")
    messages.info(request, f"Order {order.code} cancelled and stock returned.")
    return redirect(order)


@login_required
@require_POST
def request_return(request, item_id):
    item = get_object_or_404(
        OrderItem, pk=item_id, order__customer=request.user.customer
    )
    if hasattr(item, "return_request"):
        messages.info(request, "A return is already open for this item.")
        return redirect(item.order)
    if item.order.status != Order.DELIVERED:
        messages.error(request, "You can request a return once the order is delivered.")
        return redirect(item.order)

    form = ReturnRequestForm(request.POST)
    if form.is_valid():
        return_request = form.save(commit=False)
        return_request.order_item = item
        return_request.save()
        notify(request.user.customer, f"Return requested for {item.variant.product.name}.")
        log(request, f"Requested return for {item}")
        messages.success(request, "Return requested. We will reply within 2 working days.")
    else:
        messages.error(request, "Add a reason for the return.")
    return redirect(item.order)


# --------------------------------------------------------------------------
# account
# --------------------------------------------------------------------------

def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        log(request, "Created an account")
        messages.success(request, f"Welcome to {settings.SHOP_NAME}, {user.first_name}.")
        return redirect("home")
    return render(request, "account/signup.html", {"form": form})


@login_required
def profile(request):
    customer = request.user.customer
    form = ProfileForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")

    return render(
        request,
        "account/profile.html",
        {
            "form": form,
            "customer": customer,
            "order_count": customer.orders.count(),
            "review_count": customer.reviews.count(),
            "activity": customer.activity.all()[:8],
        },
    )


@login_required
def notifications(request):
    customer = request.user.customer
    notes = customer.notifications.all()
    unread = notes.filter(is_read=False)
    unread_count = unread.count()
    unread.update(is_read=True)
    return render(
        request,
        "account/notifications.html",
        {"notes": notes, "marked_read": unread_count},
    )


@login_required
@require_POST
def toggle_subscription(request):
    subscription, _ = Subscription.objects.get_or_create(customer=request.user.customer)
    subscription.is_active = not subscription.is_active
    subscription.save()
    if subscription.is_active:
        messages.success(request, "You are on the list. One letter a month, no more.")
    else:
        messages.info(request, "You will not get the newsletter any more.")
    return redirect(request.POST.get("next") or "home")
