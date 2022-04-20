from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import ugettext_lazy as _


# Create your models here.
from .Custom_Manager import CustomManager


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True, error_messages={
            'unique': _("A user with that username already exists."),
        })

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomManager()

    def __str__(self):
        return self.email