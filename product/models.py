import os

from django.db import models


# Create your models here.
from isenbergAddon.settings import MEDIA_ROOT


class Product(models.Model):
    IMAGE_BASE_URL = os.path.join(MEDIA_ROOT, 'product', 'images')

    model_no = models.CharField(max_length=100, unique=True)
    list_price = models.DecimalField(null=False, blank=False, decimal_places=2, max_digits=20)
    photo_1 = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    finish = models.CharField(null=True, blank=True, max_length=100)
    spec_sheet_file_name = models.CharField(max_length=255, null=True, blank=True)

    @property
    def get_product_photo(self):
        if self.photo_1 and os.path.exists(os.path.join(self.IMAGE_BASE_URL, self.photo_1)):
            return os.path.join(self.IMAGE_BASE_URL, self.photo_1)

    def __str__(self):
        return self.model_no



