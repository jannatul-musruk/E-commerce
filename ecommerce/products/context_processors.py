from django.conf import settings

from .models import Category


def shop_context(request):
    """Values every template needs: shop name, nav categories, bag and alerts."""
    data = {
        'shop_name': settings.SHOP_NAME,
        'shop_tagline': settings.SHOP_TAGLINE,
        'nav_categories': Category.objects.all()[:6],
        'cart_count': 0,
        'unread_notifications': 0,
        'is_subscribed': False,
    }
    if request.user.is_authenticated:
        customer = getattr(request.user, 'customer', None)
        if customer:
            cart = getattr(customer, 'cart', None)
            if cart:
                data['cart_count'] = cart.item_count
            data['unread_notifications'] = customer.notifications.filter(is_read=False).count()
            subscription = getattr(customer, 'subscription', None)
            data['is_subscribed'] = bool(subscription and subscription.is_active)
    return data
