from django.contrib import admin
from .models import Roles, User, Presentation, Transaction, Tariff

admin.site.register([
    Roles, User
])


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'updated_at',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'status', 'order_id', 'created_at']
    search_fields = ['user__username', 'amount', 'order_id', 'created_at']


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'presentation_count']
