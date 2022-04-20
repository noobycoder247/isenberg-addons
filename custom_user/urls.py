from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import path

from custom_user import views

urlpatterns = [
    path('login', views.login_user, name="login"),
    path('register', views.register_user, name="register"),
    path('logout', views.logout_user, name="logout"),
    path('', views.home, name='home'),
    path('activate/<uidb64>/<token>', views.activate_account, name='activate'),

    path('reset_password/',
         views.reset_password,
         name="reset_password"),


    path('reset/<uidb64>/<token>/',
         views.reset_password_form,
         name="password_reset_confirm"),

]
