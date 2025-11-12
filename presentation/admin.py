from django.contrib import admin
from .models import Roles, User, Presentation, Transaction, Tariff, BalanceHistory, Balance, PromoCode, PromoCodeUsage, \
    Scope

admin.site.register([
    Roles, User
])


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'updated_at', 'share_link_uid')
    search_fields = ('id', 'user__username', 'user__email', 'title', 'share_link_uid')
    list_filter = ('date_created', 'date_edited', 'group', 'removed', 'user')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'status', 'order_id', 'created_at']
    search_fields = ['user__username', 'amount', 'order_id', 'created_at']
    list_filter = ('status', 'created_at', 'user')


@admin.register(Scope)
class ScopeAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'code', 'description_short']
    list_display_links = ['id', 'title']
    search_fields = ['title', 'code', 'description']

    def description_short(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description

    description_short.short_description = 'Описание'


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active', 'scopes_count']
    list_display_links = ['name']
    list_filter = ['is_active']
    search_fields = ['name']
    filter_horizontal = ['scopes']

    def scopes_count(self, obj):
        return obj.scopes.count()

    scopes_count.short_description = 'Кол-во скоупов'


@admin.register(Balance)
class BalanceAdmin(admin.ModelAdmin):
    list_display = ['user_balance', 'amount', 'next_payment_at']
    list_filter = ['next_payment_at']
    search_fields = ['user_balance__email', 'user_balance__username']


@admin.register(BalanceHistory)
class BalanceHistoryAdmin(admin.ModelAdmin):
    list_display = ['amount_change', 'change_type', 'change_reason', 'balance', 'created_at']
    search_fields = ['balance__user_balance__username', 'balance__user_balance__email']
    list_filter = ['change_type', 'change_reason', 'created_at']


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'usage_type', 'token_amount', 'remaining_days', 'can_sum', 'usage_limit', 'is_active', 'expiration_date']
    list_filter = ['usage_type', 'can_sum', 'is_active']
    search_fields = ['code']


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'promo_code', 'applied_at')
    list_filter = ('applied_at',)
    search_fields = ('user__username', 'promo_code__code')