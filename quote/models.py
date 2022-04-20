from django.db import models

# Create your models here.
from custom_user.models import CustomUser
from product.models import Product
from utilities.models import TimeStampedModelOnly
from django.conf import settings
User = settings.AUTH_USER_MODEL



class Quote(TimeStampedModelOnly):
    job_name = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def all_quote_items_area_wise(self):
        lineItems = QuoteLineItem.objects.filter(quote=self)
        print(lineItems)
        dc = dict()
        for item in lineItems:
            print(item.area)
            if item.area in dc:
                dc[item.area].append(item)
            else:
                dc[item.area] = [item]
        print(dc)
        return dc
    def __str__(self):
        return self.job_name + str(self.created_by)



class QuoteArea(models.Model):
    area = models.CharField(max_length=150, null=False, blank=False)


    def __str__(self):
        return self.area


class QuoteLineItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    area = models.ForeignKey(QuoteArea, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(null=False, blank=False)
    list_price = models.PositiveIntegerField(null=False, blank=False)


