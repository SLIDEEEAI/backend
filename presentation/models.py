from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import models
from django.utils.timezone import now, timedelta
import uuid


from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin
)

from presentation.manager import UserManager


class Roles(models.Model):
    name = models.CharField(max_length=128)

    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return f"{self.id}) {self.name.title()}"


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Balance(BaseModel):
    """
    Модель для отслеживания баланса пользователя.

    Поля:
        id (UUID): Уникальный идентификатор баланса (UUID).
        amount (Decimal): Сумма на балансе пользователя.
        last_update_event_id (UUID): Идентификатор последнего события обновления баланса.
        next_payment_at (DateTimeField): Время когда нужно будет сделать следующую оплату по тарифу
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=90)
    next_payment_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        """
        Возвращает строковое представление объекта Balance.

        Returns:
            str: Сумма на балансе пользователя и юзернейм в виде строки.
        """
        user = getattr(self, 'user_balance', 'N/A')
        return f'{user} - {str(self.amount)}'

    class Meta:
        """
        Название таблицы в базе данных
        """

        db_table = 'balance'


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255)
    email = models.EmailField(db_index=True, unique=True)
    role = models.ForeignKey(Roles, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    balance = models.OneToOneField(Balance, on_delete=models.DO_NOTHING, related_name='user_balance', null=True)
    presentation = models.IntegerField(default=0)
    referrer = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referrals'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def token(self):
        return self._generate_jwt_token()

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def _generate_jwt_token(self):

        refresh = RefreshToken.for_user(self)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class Presentation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    author = models.IntegerField(null=True)
    title = models.CharField(max_length=255, null=True)
    group = models.IntegerField(null=True)
    favourite = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    date_created = models.DateTimeField(null=True)
    date_edited = models.DateTimeField(null=True)
    theme = models.IntegerField(null=True)
    json = models.JSONField()
    share_link_uid = models.UUIDField(default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return f"Presentation ({self.id}) {self.user}"


class Picture(models.Model):
    hash_name = models.TextField()
    source = models.ImageField(upload_to='pictures', default=None, null=True)

class GeneratedImage(models.Model):
    theme = models.CharField(max_length=255)
    image = models.ImageField(upload_to='generated_images/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for theme: {self.theme}"


class Transaction(BaseModel):
    class Statuses(models.TextChoices):
        """
        Перечисление возможных статусов транзакции.
        """
        CREATED = 'CR', 'created'
        CARD_SEARCH = 'CS', 'card_search'
        WAITING_PAYMENT = 'WP', 'waiting_payment'
        REJECTED_TIMEOUT = 'RT', 'rejected_timeout'
        REJECT_BY_OFFICE = 'RO', 'reject_by_office'
        REJECT_MANUAL_BY_CLIENT = 'RC', 'reject_manual_by_client'
        PROCEEDINGS = 'PR', 'proceedings'
        PROCEEDINGSN = 'PN', 'proceedingsN'
        COMPLETED = 'CM', 'completed'
        REJECT_BY_SYSTEM = 'RS', 'rejected_by_system'
        REJECT_BY_NEW_DEAL = 'RD', 'rejected_by_new_deal'

    @classmethod
    def get_status_code(cls, state: str) -> str:
        """
        Возвращает код статуса по его строковому представлению.

        Args:
            state (str): Строковое представление статуса.

        Returns:
            str: Код статуса.
        """
        return cls.Statuses.__members__.get(state.upper())

    uuid = models.UUIDField(primary_key=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_transaction', null=True)
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=3, choices=Statuses.choices, help_text="Статусы")
    payment_url = models.URLField(max_length=1000)


class Tariff(BaseModel):
    """
    Модель для хранения информации о тарифах.

    Поля:
        id (UUIDField): Уникальный идентификатор тарифа.
        name (CharField): Название тарифа.
        price_per_day (DecimalField): Стоимость тарифа за день.

    Methods:
        __str__(): Возвращает строковое представление объекта.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    presentation_count = models.IntegerField()

    def __str__(self) -> str:
        """
        Возвращает строковое представление объекта.

        Returns:
            str: Название тарифа.
        """
        return self.name


class BalanceHistory(BaseModel):
    """
    Модель для сохранения действий, связанных с балансом пользователя.

    Поля:
        id (UUID): Уникальный идентификатор записи истории баланса (UUID).
        amount_change (Decimal): Изменение суммы на балансе.
        change_type (str): Тип изменения (увеличение/уменьшение).
        change_reason (str): Причина изменения баланса.
        balance (Balance): Связь с объектом баланса.
    """

    class Reason(models.TextChoices):
        """
        Перечисление возможных причин изменения баланса пользователя.
        """
        SLIDE_PAYMENT = 'SP', 'Оплата Генерации слайдов'
        TOP_UP = 'TU', 'Пополнение'
        BONUS_TOP_UP = 'BT', 'Бонус за пополнение'
        BONUS_REGISTRATION = 'BNU', 'Бонус за регистрацию'
        REFERRAL_TOP_UP = 'RT', 'Реферальный бонус'
        PROMOTIONAL_CODE = 'PC', 'Промокод'
        ACTIVITY_BONUS = 'AB', 'Бонус за активность'

    class ChangeType(models.TextChoices):
        """
        Перечисление возможных типов изменения баланса (увеличение/уменьшение).
        """
        INCREASE = 'Incr', 'Increase'
        DECREASE = 'Decr', 'Decrease'

    id = models.UUIDField(primary_key=True,
                          default=uuid.uuid4,
                          editable=False,
                          help_text="Уникальный идентификатор записи истории баланса (UUID)")
    amount_change = models.DecimalField(max_digits=10,
                                        decimal_places=2,
                                        help_text="Изменение суммы на балансе")
    change_type = models.CharField(max_length=4,
                                   choices=ChangeType.choices,
                                   help_text="Тип изменения (увеличение/уменьшение)")
    change_reason = models.CharField(max_length=3, choices=Reason.choices, help_text="Причина изменения баланса")
    balance = models.ForeignKey('Balance',
                                on_delete=models.CASCADE,
                                related_name='histories',
                                null=False,
                                help_text="Связь с объектом баланса")

    def __str__(self) -> str:
        """
        Возвращает строковое представление объекта BalanceHistory.

        Returns:
            str: Строковое представление в виде строки.
        """

        return f"{self.amount_change!s} {self.get_change_type_display()} {self.get_change_reason_display()}"

    class Meta:
        """
        Название таблицы в базе данных и индексирование полей:
        - created_at
        - change_type
        - change_reason
        """
        indexes = [
            models.Index(fields=['created_at', 'change_type', 'change_reason'], name='balance_history_index')
        ]
        db_table = 'balance_history'


class PromoCode(models.Model):
    SINGLE_USE = 'single'
    MULTI_USE = 'multi'

    USAGE_TYPE_CHOICES = [
        (SINGLE_USE, 'Одноразовый'),
        (MULTI_USE, 'Многоразовый'),
    ]

    code = models.CharField(max_length=255, unique=True)  # Уникальный код промокода
    usage_type = models.CharField(max_length=10, choices=USAGE_TYPE_CHOICES)
    usage_limit = models.PositiveIntegerField(default=1)  # Сколько раз можно использовать (для многоразовых)
    expiration_date = models.DateField()  # Дата окончания действия
    can_sum = models.BooleanField(default=False)  # Суммируется ли с другими промокодами
    is_active = models.BooleanField(default=True)  # Флаг активности

    token_amount = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    def remaining_days(self):
        """Возвращает количество дней до окончания действия."""
        return (self.expiration_date - now().date()).days

    def is_expired(self):
        """Проверяет, истёк ли срок действия промокода."""
        return now().date() > self.expiration_date


class PromoCodeUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE)
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} использовал {self.promo_code.code}"