from django.contrib import admin
from .models import *

# Register your models here.





@admin.register(SliderItem)
class SliderItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'season')
    search_fields = ('title', 'season')

@admin.register(ShopBanner)
class ShopBannerAdmin(admin.ModelAdmin):
    list_display = ('id',)
    search_fields = ('id',)



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'discount_price', 'in_stock', 'sku')
    list_filter = ('in_stock', 'categories', 'tags', 'sizes', 'colors')
    search_fields = ('title', 'sku', 'brand', 'manufacturer')
    filter_horizontal = ('sizes', 'colors', 'categories', 'tags', 'images', 'ProductDescriptionBoxes')

# Register other models as usual
admin.site.register(ProductImage)
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Size)
admin.site.register(Color)
admin.site.register(ProductDescriptionBox)