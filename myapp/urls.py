from django.urls import path  # Import the 'path' function to define URL patterns
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

    path('login/', login, name='login'),
    path('register/', register, name='register'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)