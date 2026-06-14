from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .models import Roles, User, Presentation, Transaction, Tariff, BalanceHistory, Balance, PromoCode, PromoCodeUsage, \
    Scope, GeneratedImage

admin.site.register([
    Roles
])


class UserPresentationInline(admin.TabularInline):
    model = Presentation
    fk_name = 'user'
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ('-created_at',)
    fields = ('id', 'title', 'created_at', 'updated_at', 'favourite', 'removed', 'share_link_uid')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    class Media:
        css = {
            'all': ('presentation/admin/user_presentations_inline.css',)
        }


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'username', 'email_verified', 'tariff', 'last_login', 'created_at')
    search_fields = ('id', 'email', 'username')
    list_filter = ('email_verified', 'tariff', 'last_login')
    readonly_fields = (
        'last_login',
        'created_at',
        'updated_at',
        'payment_history',
        'promo_code_history',
        'referral_history',
    )
    inlines = (UserPresentationInline,)

    @admin.display(description='История платежей')
    def payment_history(self, obj):
        if not obj or not obj.balance_id:
            return 'Нет записей'

        histories = BalanceHistory.objects.filter(balance=obj.balance).order_by('-created_at')
        rows = (
            (
                history.amount_change,
                history.get_change_type_display(),
                history.get_change_reason_display(),
                self._format_datetime(history.created_at),
            )
            for history in histories
        )
        return self._render_history_table(
            headers=('Стоимость', 'Тип', 'Причина', 'Дата и время'),
            rows=rows,
        )

    @admin.display(description='История ввода промокодов')
    def promo_code_history(self, obj):
        if not obj:
            return 'Нет записей'

        usages = PromoCodeUsage.objects.filter(user=obj).select_related('promo_code').order_by('-applied_at')
        rows = (
            (
                usage.promo_code.code,
                usage.promo_code.token_amount,
                self._format_datetime(usage.applied_at),
            )
            for usage in usages
        )
        return self._render_history_table(
            headers=('Промокод', 'Кол-во токенов', 'Дата и время'),
            rows=rows,
        )

    @admin.display(description='История рефералов')
    def referral_history(self, obj):
        if not obj:
            return 'Нет записей'

        referrals = obj.referrals.order_by('-created_at')
        rows = (
            (
                referral.id,
                referral.email,
                referral.username,
                self._format_datetime(referral.created_at),
            )
            for referral in referrals
        )
        return self._render_history_table(
            headers=('ID', 'Email', 'Username', 'Дата приглашения'),
            rows=rows,
        )

    @staticmethod
    def _format_datetime(value):
        if not value:
            return '-'
        return timezone.localtime(value).strftime('%d.%m.%Y %H:%M:%S')

    @staticmethod
    def _render_history_table(headers, rows):
        rows = tuple(rows)
        if not rows:
            return 'Нет записей'

        header_html = format_html_join('', '<th>{}</th>', ((header,) for header in headers))
        rows_html = format_html_join(
            '',
            '<tr>{}</tr>',
            (
                (format_html_join('', '<td>{}</td>', ((cell,) for cell in row)),)
                for row in rows
            )
        )
        return format_html(
            '<div class="admin-history-table-wrapper">'
            '<table class="admin-history-table">'
            '<thead><tr>{}</tr></thead>'
            '<tbody>{}</tbody>'
            '</table>'
            '</div>',
            header_html,
            rows_html,
        )

    class Media:
        css = {
            'all': ('presentation/admin/user_presentations_inline.css',)
        }


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at', 'updated_at', 'share_link_uid')
    search_fields = ('id', 'user__username', 'user__email', 'title', 'share_link_uid')
    list_filter = ('favourite', 'removed', 'created_at', 'updated_at', 'user')
    readonly_fields = ('id', 'share_link_uid', 'created_at', 'updated_at')
    fields = ('id', 'user', 'title', 'favourite', 'removed', 'json', 'share_link_uid', 'created_at', 'updated_at')


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
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


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


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'theme_short', 'image', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('theme', 'user')
    readonly_fields = ('created_at',)

    @admin.display(description='Тема')
    def theme_short(self, obj):
        if len(obj.theme) <= 100:
            return obj.theme
        return f'{obj.theme[:100]}...'