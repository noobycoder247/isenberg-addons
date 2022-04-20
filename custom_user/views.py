from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import BaseUserManager

# Create your views here.
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from custom_user.models import CustomUser
from custom_user.tokens import generate_token


def user_is_not_logged_in(user):
    return not user.is_authenticated()


def login_user(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        _user = CustomUser.objects.filter(email=email).first()
        user = authenticate(request=request, email=email, password=password)
        print(user)
        if user is not None and _user.is_active:
            login(request=request, user=user)
            return redirect('home')
        elif _user and not _user.is_active:
            messages.error(request, message="Account is not active.")
            return redirect('login')
        elif _user is None:
            messages.info(request, message="This email doesn't register yet.")
            return redirect('register')
        else:
            messages.error(request, message="Email and Password didn't match.")
            return redirect('login')

    return render(request, template_name='login.html')


def home(request):
    return render(request, template_name='index.html')


def register_user(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        cnf_password = request.POST['cnf_password']
        user = CustomUser.objects.filter(email=email)
        email = BaseUserManager.normalize_email(email)
        if user:
            messages.warning(request, message="This email is already registered please login")
            return redirect('login')
        elif password != cnf_password:
            messages.error(request, message="Password and Confirm Password doesn't match")
            return redirect('register')
        else:
            user = CustomUser.objects.create_user(email, password)
            user.is_active = False
            user.save()

            # Confirmation email
            current_site = get_current_site(request)
            email_subject = "Confirmation Email for @Isenberg"
            body = render_to_string('confirmation-email-template.html',
                                    {
                                        'domain': current_site.domain,
                                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                                        'token': generate_token.make_token(user)
                                    }
                                    )
            email = EmailMessage(
                email_subject,
                body,
                settings.EMAIL_HOST_USER,
                [user.email],
            )
            email.fail_silently = True
            email.send()

            messages.success(request, message="We sent a confirmation mail to your email please activate your account")
            return redirect('login')

    return render(request, template_name='register.html')


@login_required(redirect_field_name='next', login_url='login')
def logout_user(request):
    logout(request)
    return redirect('home')


def activate_account(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and generate_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, message='Account activated successfully now please login')
        return redirect('login')
    else:
        return render(request, 'activation-failed.html')


def reset_password(request):
    if request.method == 'POST':
        email_id = request.POST['email']
        email_id = BaseUserManager.normalize_email(email_id)
        user = CustomUser.objects.filter(email=email_id).first()
        if user is not None:
            # Confirmation email
            current_site = get_current_site(request)
            email_subject = "Reset Password for @Isenberg"
            body = render_to_string('reset-password-email-template.html',
                                    {
                                        'domain': current_site.domain,
                                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                                        'token': generate_token.make_token(user)
                                    }
                                    )
            email = EmailMessage(
                email_subject,
                body,
                settings.EMAIL_HOST_USER,
                [user.email],
            )
            email.fail_silently = True
            email.send()
        return render(request, template_name='password_reset_sent.html', context={'email': email_id})

    return render(request, template_name='password_reset.html')


def reset_password_form(request, uidb64, token):
    if request.method == 'POST':
        password1 = request.POST['password_1']
        password2 = request.POST['password_2']
        if password1 != password2:
            messages.error("Password and Confirm Password doesn't match ")
            return redirect('password_reset_confirm')
        else:
            try:
                uid = force_text(urlsafe_base64_decode(uidb64))
                user = CustomUser.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
                user = None

            if user is not None and generate_token.check_token(user, token):
                user.set_password(password1)
                user.save()
                messages.success(request, message='Password reset successfully!')
                return redirect('login')
            else:
                return render(request, 'activation-failed.html', context={'password_reset': True})

    return render(request, 'password_reset_form.html')
