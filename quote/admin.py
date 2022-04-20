from django.contrib import admin
from quote.models import Quote, QuoteArea, QuoteLineItem

# Register your models here.

admin.site.register(Quote)
admin.site.register(QuoteArea)
admin.site.register(QuoteLineItem)
