from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    # =========================
    # PUBLIC / AUTH
    # =========================
    path('', views.home, name='home'),

    path('login/',    views.login_view,    name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),


    # =========================
    # DASHBOARDS
    # =========================
    path('admin-dashboard/',  views.admin_dashboard,  name='admin_dashboard'),
    path('seller-dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('user-dashboard/',   views.user_dashboard,   name='user_dashboard'),


    # =========================
    # ADMIN
    # =========================
    path('delete-seller/<int:seller_id>/', views.delete_seller, name='delete_seller'),

    path('dashboard/admin/products/', views.admin_view_products, name='admin_view_products'),
    path('dashboard/admin/orders/',   views.admin_view_orders,   name='admin_view_orders'),

    path('dashboard/admin/seller/<int:seller_id>/',        views.admin_view_seller, name='admin_view_seller'),
    path('dashboard/admin/delete-seller/<int:seller_id>/', views.delete_seller,      name='delete_seller'),


    # =========================
    # SELLER
    # =========================
    path('seller/profile/',         views.seller_profile,        name='seller_profile'),
    path('seller/profile/update/',  views.update_seller_profile, name='update_seller_profile'),

    path('seller/add-shop/',                    views.add_shop,    name='add_shop'),
    path('seller/shop/<int:shop_id>/edit/',     views.edit_shop,   name='edit_shop'),
    path('seller/shop/<int:shop_id>/delete/',   views.delete_shop, name='delete_shop'),

    path('seller/add-product/',                  views.add_product,   name='add_product'),
    path('seller/products/',                     views.products_list, name='products_list'),
    path('seller/product/edit/<int:product_id>/',   views.edit_product,   name='edit_product'),
    path('seller/product/delete/<int:product_id>/', views.delete_product, name='delete_product'),


    # =========================
    # USER
    # =========================
    path('user-profile/', views.user_profile, name='user_profile'),

    path('user/profile/upload-image/', views.upload_profile_image, name='upload_profile_image'),

    path('address/add/',                 views.add_address,    name='add_address'),
    path('address/<int:address_id>/edit/',   views.edit_address,   name='edit_address'),
    path('address/<int:address_id>/delete/', views.delete_address, name='delete_address'),

    path('add-review/', views.add_review, name='add_review'),

    path('buy-now-order/', views.create_buy_now_order, name='create_buy_now_order'),

    path('add-to-cart/<int:product_id>/',           views.add_to_cart,            name='add_to_cart'),
    path('cart/',                                   views.cart_page,              name='cart'),
    path('cart/update/<int:item_id>/<str:action>/', views.update_cart_quantity,   name='update_cart'),
    path('cart/remove/<int:item_id>/',              views.remove_from_cart,       name='remove_from_cart'),

    path('cart/confirm-order/', views.confirm_order, name='confirm_cart_order'),
    path('orders/',             views.orders_page,   name='orders_page'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
