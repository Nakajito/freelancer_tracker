from allauth.account.forms import LoginForm, SignupForm
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.accounts.turnstile import validate_turnstile


User = get_user_model()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "avatar",
            "language_preference",
        ]
        labels = {
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "email": _("Email"),
            "avatar": _("Profile image"),
            "language_preference": _("Language"),
        }


class PreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["language_preference"]


class DeactivateAccountForm(forms.Form):
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        strip=False,
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(_("Enter your current password to continue."))
        return password


class TurnstileFormMixin:
    def clean(self):
        cleaned_data = super().clean()
        token = self.data.get("cf-turnstile-response", "")
        request = getattr(self, "request", None)
        remote_ip = request.META.get("REMOTE_ADDR", "") if request else ""
        validate_turnstile(token, remote_ip)
        return cleaned_data


class TurnstileLoginForm(TurnstileFormMixin, LoginForm):
    pass


class TurnstileSignupForm(TurnstileFormMixin, SignupForm):
    pass
