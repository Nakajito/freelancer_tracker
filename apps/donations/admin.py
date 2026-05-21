from django.contrib import admin

from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = (
        "amount",
        "currency",
        "provider",
        "status",
        "frequency",
        "email",
        "created_at",
    )
    list_filter = ("provider", "status", "frequency")
    search_fields = ("email", "provider_payment_id", "provider_pref_id")
    readonly_fields = (
        "created_at",
        "updated_at",
        "provider_payment_id",
        "provider_pref_id",
    )
