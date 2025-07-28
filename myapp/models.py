import os

from django.db import models


# Create your models here.


class SliderItem(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='slider_images/')
    season = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        # Delete the image file from storage
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

class ShopBanner(models.Model):
    image = models.ImageField(upload_to='shop_banner/')


    def __str__(self):
        return f"Shop Banner {self.id}"
    def delete(self, *args, **kwargs):
        # Delete the image file from storage
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)





class Size(models.Model):
    name = models.CharField(max_length=10)
    def __str__(self): 
        return self.name

class Color(models.Model):
    name = models.CharField(max_length=30)
    hex_code = models.CharField(max_length=7)
    def __str__(self): 
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): 
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self): 
        return self.name

class ProductImage(models.Model):
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    def __str__(self): 
        return self.alt_text or f"Image {self.id}"

class ProductDescriptionBox(models.Model):
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.title}"
    

class Product(models.Model):
    title = models.CharField(max_length=255)
    title2 = models.CharField(max_length=255, blank=True, null=True)
    mini_description = models.TextField(max_length=300)
    description = models.TextField()

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    in_stock = models.BooleanField(default=True)

    sizes = models.ManyToManyField(Size, blank=True)
    colors = models.ManyToManyField(Color, blank=True)
    categories = models.ManyToManyField(Category, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    images = models.ManyToManyField(ProductImage, related_name='products', blank=True)
    ProductDescriptionBoxes = models.ManyToManyField('ProductDescriptionBox', blank=True, related_name='products')

    manufacturer = models.CharField(max_length=255)
    country_of_origin = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    included_components = models.CharField(max_length=255)
    dimensions = models.CharField(max_length=100)
    brand = models.CharField(max_length=255)

    def delete(self, *args, **kwargs):
        # Delete all related images
        for image in self.images.all():
            image.delete()
        super().delete(*args, **kwargs)