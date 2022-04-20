from django.urls import path

from quote.views import test_view

urlpatterns = [
    path('', test_view, name="quote_view"),
]