from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    ActivityLog,
    Brand,
    Cart,
    CartItem,
    Category,
    Customer,
    CustomUser,
    Notification,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
    ReturnRequest,
    Review,
    ShippingAddress,
    Subscription,
    Wishlist,
)

admin.site.site_header = "Nokshi admin"
admin.site.site_title = "Nokshi admin"
admin.site.index_title = "Shop management"


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Extra", {"fields": ("middle_name",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra", {"fields": ("email", "first_name", "last_name", "middle_name")}),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city", "joined_at")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "origin")
    prepopulated_fields = {"slug": ("name",)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "starting_price", "total_stock", "is_featured", "is_active")
    list_filter = ("category", "brand", "is_featured", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "sku", "price", "compare_at_price", "stock")
    list_filter = ("product__category",)
    list_editable = ("price", "compare_at_price", "stock")
    search_fields = ("sku", "product__name")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("customer", "item_count", "subtotal", "created_at")
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price",)


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0


class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("code", "customer", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("code", "customer__user__username")
    readonly_fields = ("code", "subtotal", "delivery_charge", "total")
    inlines = [OrderItemInline, PaymentInline, ShippingAddressInline]
    actions = ["mark_confirmed", "mark_shipped", "mark_delivered"]

    def _set_status(self, request, queryset, status, label):
        updated = queryset.update(status=status)
        for order in queryset:
            Notification.objects.create(
                customer=order.customer,
                message=f"Order {order.code} is {label}.",
                link=order.get_absolute_url(),
            )
        self.message_user(request, f"{updated} order(s) marked {label}.")

    @admin.action(description="Mark selected orders as confirmed")
    def mark_confirmed(self, request, queryset):
        self._set_status(request, queryset, Order.CONFIRMED, "confirmed")

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        self._set_status(request, queryset, Order.SHIPPED, "on the way")

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        self._set_status(request, queryset, Order.DELIVERED, "delivered")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "method", "is_paid", "paid_at")
    list_filter = ("method", "is_paid")


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("order", "recipient_name", "city", "country")
    search_fields = ("recipient_name", "city")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "customer", "rating", "created_at")
    list_filter = ("rating",)


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("order_item", "status", "requested_at")
    list_filter = ("status",)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "added_at")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("customer", "is_active", "subscribed_at")
    list_filter = ("is_active",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("customer", "message", "is_read", "created_at")
    list_filter = ("is_read",)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("customer", "action", "created_at")
    list_filter = ("created_at",)
    search_fields = ("action",)
