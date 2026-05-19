from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import UpdateView

from apps.accounts.forms import (
    DeactivateAccountForm,
    PreferencesForm,
    ProfileForm,
)


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("account-profile")

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["deactivate_form"] = DeactivateAccountForm(user=self.request.user)
        return context

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        response = super().form_valid(form)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            self.object.language_preference,
            path="/",
            samesite="Lax",
        )
        return response


class PreferencesView(LoginRequiredMixin, View):
    def post(self, request):
        form = PreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            response = redirect(request.headers.get("referer") or "dashboard")
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                user.language_preference,
                path="/",
                samesite="Lax",
            )
            messages.success(request, "Preferences updated.")
            return response

        messages.error(request, "Could not update preferences.")
        return redirect(request.headers.get("referer") or "dashboard")

    def get(self, request):
        return HttpResponseNotAllowed(["POST"])


class DeactivateAccountView(LoginRequiredMixin, View):
    template_name = "accounts/profile.html"

    def get(self, request):
        return redirect("account-profile")

    def post(self, request):
        form = DeactivateAccountForm(request.POST, user=request.user)
        if not form.is_valid():
            profile_form = ProfileForm(instance=request.user)
            return render(
                request,
                self.template_name,
                {
                    "form": profile_form,
                    "deactivate_form": form,
                    "object": request.user,
                },
            )

        user = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        logout(request)
        messages.success(request, "Your account has been deactivated.")
        return redirect("account_login")
