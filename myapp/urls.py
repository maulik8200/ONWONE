from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('', home, name='home'),


    path('shop/', shop, name='shop'),
    path('product/<int:id>/', product_detail, name='product_detail'),
    

    path('about/', about, name='about'),
    path('faq/', faq, name='faq'),
    path('contact/', contact, name='contact'),
    path('wishlist/', wishlist, name='wishlist'),
    path('cart/', cart, name='cart'),
    path('add-to-cart/<int:id>/', add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:id>/', remove_from_cart, name='remove_from_cart'),
    path('apply_coupon/', apply_coupon, name='apply_coupon'),
    path('remove_coupon/', remove_coupon, name='remove_coupon'),
    path('add_address/', add_address, name='add_address'),
    path('checkout/', checkout, name='checkout'),

    path('login/', login, name='login'),
    path('register/', register, name='register'),
    path('logout/', logout, name='logout'),
    
    path('account/', account, name='account'),
    path('account-billing-address/', account_billing_address, name='account-billing-address'),
    path('account-billing-address-2/', account_billing_address_2, name='account-billing-address-2'),
    path('edit-billing-address/<int:address_id>/', edit_billing_address, name='edit_billing_address'),
    path('remove-billing-address/<int:address_id>/', remove_billing_address, name='remove_billing_address'),

    path('upload-excel/', upload_products_excel, name='upload_products_excel'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)