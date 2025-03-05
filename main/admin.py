from django.contrib import admin

from main.models import Config


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ("referral_bonus", "bonus_to_new_users")

    def has_add_permission(self, request):
        return False if Config.objects.exists() else super().has_add_permission(request)

