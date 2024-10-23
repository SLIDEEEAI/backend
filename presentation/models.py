from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
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


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255)
    email = models.EmailField(db_index=True, unique=True)
    role = models.ForeignKey(Roles, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    balance = models.IntegerField(default=100)  # Добавлено поле для баланса
    presentation = models.IntegerField(default=0)

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


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
