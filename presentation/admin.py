import json
from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Sum
from django.http import JsonResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .models import Roles, User, Presentation, Transaction, Tariff, BalanceHistory, Balance, PromoCode, PromoCodeUsage, \
    Scope, GeneratedImage

admin.site.register([
    Roles
])

ONLINE_USERS_WINDOW = timedelta(minutes=2)


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
    change_list_template = 'admin/presentation/user/change_list.html'
    list_display = ('id', 'email', 'username', 'email_verified', 'tariff', 'online_status', 'last_seen_at', 'last_login', 'created_at')
    search_fields = ('id', 'email', 'username')
    list_filter = ('email_verified', 'tariff', 'last_seen_at', 'last_login')
    readonly_fields = (
        'online_indicator',
        'last_login',
        'last_seen_at',
        'created_at',
        'updated_at',
        'payment_history',
        'promo_code_history',
        'referral_history',
    )
    inlines = (UserPresentationInline,)

    @admin.display(description='Онлайн', boolean=True)
    def online_status(self, obj):
        return bool(obj.last_seen_at and obj.last_seen_at >= self._online_threshold())

    @admin.display(description='Статус онлайн')
    def online_indicator(self, obj):
        if not obj:
            return '-'

        is_online = self.online_status(obj)
        color = '#2e7d32' if is_online else '#ba2121'
        label = 'Онлайн' if is_online else 'Офлайн'
        last_seen = self._format_datetime(obj.last_seen_at)

        return format_html(
            '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
            'background:{};margin-right:6px;"></span>'
            '<strong>{}</strong> <span style="color:#666;">(последняя активность: {})</span>',
            color,
            label,
            last_seen,
        )

    def get_urls(self):
        custom_urls = [
            path(
                'online-users-count/',
                self.admin_site.admin_view(self.online_users_count_view),
                name='presentation_user_online_users_count',
            ),
        ]
        return custom_urls + super().get_urls()

    def online_users_count_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied

        return JsonResponse({
            'online_users_count': self._get_online_users_count(),
            'online_users_window_minutes': self._online_window_minutes(),
        })

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['online_users_count'] = self._get_online_users_count()
        extra_context['online_users_window_minutes'] = self._online_window_minutes()
        extra_context['online_users_count_url'] = reverse('admin:presentation_user_online_users_count')
        return super().changelist_view(request, extra_context=extra_context)

    @staticmethod
    def _online_threshold():
        return timezone.now() - ONLINE_USERS_WINDOW

    @classmethod
    def _get_online_users_count(cls):
        return User.objects.filter(last_seen_at__gte=cls._online_threshold()).count()

    @staticmethod
    def _online_window_minutes():
        return int(ONLINE_USERS_WINDOW.total_seconds() // 60)

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
    readonly_fields = ('id', 'share_link_uid', 'created_at', 'updated_at', 'pretty_json')
    fields = ('id', 'user', 'title', 'favourite', 'removed', 'share_link_uid', 'created_at', 'updated_at', 'pretty_json')

    @admin.display(description='JSON')
    def pretty_json(self, obj):
        value = obj.json
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass

        formatted_json = json.dumps(value, ensure_ascii=False, indent=2)
        return format_html('<pre class="pretty-json-field">{}</pre>', formatted_json)

    class Media:
        css = {
            'all': ('presentation/admin/user_presentations_inline.css',)
        }


class TariffAmountListFilter(admin.SimpleListFilter):
    title = 'Тариф / стоимость тарифа'
    parameter_name = 'tariff'

    def lookups(self, request, model_admin):
        tariffs = Tariff.objects.order_by('price', 'name')
        return (
            (str(tariff.pk), self._get_tariff_label(tariff))
            for tariff in tariffs
        )

    def queryset(self, request, queryset):
        tariff_id = self.value()
        if not tariff_id:
            return queryset

        tariff = Tariff.objects.filter(pk=tariff_id).first()
        if not tariff:
            return queryset

        amounts = {tariff.price}
        if tariff.special_price is not None:
            amounts.add(tariff.special_price)

        return queryset.filter(amount__in=amounts)

    @staticmethod
    def _get_tariff_label(tariff):
        if tariff.special_price is not None:
            return f'{tariff.name}: {tariff.special_price} (обычная {tariff.price})'
        return f'{tariff.name}: {tariff.price}'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    change_list_template = 'admin/presentation/transaction/change_list.html'
    list_display = ['user', 'amount', 'currency', 'status', 'tariff_by_amount', 'order_id', 'created_at']
    search_fields = ['user__username', 'user__email', 'amount', 'order_id', 'created_at']
    list_filter = ('status', TariffAmountListFilter, 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    @admin.display(description='Тариф по стоимости')
    def tariff_by_amount(self, obj):
        tariff = Tariff.objects.filter(price=obj.amount).first()
        if not tariff:
            tariff = Tariff.objects.filter(special_price=obj.amount).first()
        return tariff.name if tariff else '-'

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        try:
            queryset = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        summary = queryset.aggregate(
            average_amount=Avg('amount'),
            total_amount=Sum('amount'),
            transactions_count=Count('uuid'),
        )
        response.context_data['transaction_summary'] = {
            'average_amount': summary['average_amount'],
            'total_amount': summary['total_amount'],
            'transactions_count': summary['transactions_count'],
        }
        return response

    class Media:
        css = {
            'all': ('presentation/admin/user_presentations_inline.css',)
        }


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
    list_display = [
        'code',
        'usage_type',
        'user_access',
        'token_amount',
        'usage_limit',
        'usages_count',
        'remaining_days',
        'can_sum',
        'is_active',
        'expiration_date'
    ]
    list_filter = ['usage_type', 'user_access', 'can_sum', 'is_active']
    search_fields = ['code']

    @admin.display(description='Использований')
    def usages_count(self, obj):
        return PromoCodeUsage.objects.filter(promo_code=obj).count()


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