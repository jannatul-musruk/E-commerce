from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    # storefront
    path('', views.home, name='home'),
    path('shop/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<slug:slug>/review/', views.add_review, name='add_review'),

    # cart
    path('bag/', views.cart_detail, name='cart_detail'),
    path('bag/add/<int:variant_id>/', views.cart_add, name='cart_add'),
    path('bag/update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('bag/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),

    # wishlist
    path('saved/', views.wishlist_view, name='wishlist'),
    path('saved/toggle/<slug:slug>/', views.wishlist_toggle, name='wishlist_toggle'),

    # checkout and orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/cancel/', views.order_cancel, name='order_cancel'),
    path('orders/item/<int:item_id>/return/', views.request_return, name='request_return'),

    # account
    path('signup/', views.signup, name='signup'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='account/login.html',
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('notifications/', views.notifications, name='notifications'),
    path('newsletter/', views.toggle_subscription, name='toggle_subscription'),
]
