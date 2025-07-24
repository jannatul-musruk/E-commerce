from django.contrib import admin
from .models import CustomUser, Customer, Category, Brand, Product, ProductVariant, Cart, CartItem, Order, OrderItem, Payment, ShippingAddress, Wishlist, Review, ReturnRequest, Subscription, Notification, ActivityLog

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Customer)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(ShippingAddress)
admin.site.register(Wishlist)
admin.site.register(Review)
admin.site.register(ReturnRequest)
admin.site.register(Subscription)
admin.site.register(Notification)
admin.site.register(ActivityLog)