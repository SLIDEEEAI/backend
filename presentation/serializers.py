import os
from typing import Dict, Any, List

from django.contrib.auth import authenticate, password_validation
from django.core.cache import cache

from django.core.exceptions import ValidationError

from django.db.models import F, Case, When, DecimalField

from django.forms.models import model_to_dict

from collections import OrderedDict

from .models import Roles, Presentation, Tariff, BalanceHistory, PromoCode, PromoCodeUsage, Scope
from rest_framework.serializers import ValidationError

from .services import generate_slides_text, generate_slides_with_templates

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from datetime import date


from rest_framework import serializers
from .models import User



class GPTRequestSerializer(serializers.Serializer):
    gpt_request = serializers.CharField(
        required=True
    )

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        return token


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )
    role = serializers.ListField(child=serializers.IntegerField(write_only=True))
    token = serializers.DictField(read_only=True)
    promocode = serializers.SlugRelatedField(
        slug_field='code',
        queryset=PromoCode.objects.filter(is_active=True),
        write_only=True,
        required=False,
    )
    referral_user = serializers.SlugRelatedField(
        slug_field='pk',
        queryset=User.objects.all(),
        write_only=False,
        required=False,
    )

    class Meta:
        model = User
        fields = ['email', 'username', 'role', 'password', 'token', 'referral_user', 'promocode']

    def validate(self, attrs: OrderedDict):
        db_roles = set(Roles.objects.values_list("id", flat=True))
        incoming_roles = set(attrs["role"])

        if not incoming_roles.issubset(db_roles):
            raise serializers.ValidationError(
                "Available roles for registration - {}".format(", ".join(map(str, db_roles)))
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("referral_user", None)
        validated_data.pop("promocode", None)

        user = User.objects.create_user(**validated_data)
        user_dict = model_to_dict(user)
        user_dict.update({"token": user.token})

        return user_dict


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=128, write_only=True
    )
    new_password = serializers.CharField(
        max_length=128, write_only=True, required=True
    )

    def validate_user_password(self, password, user):
        user = authenticate(username=user.email, password=password)

        if user is None: raise serializers.ValidationError(
            'email or password is incorrect!'
        )

        if not user.is_active: raise serializers.ValidationError(
            'This user has been deactivated.'
        )

    def validate_new_password(self, password):
        try:
            password_validation.validate_password(
                password=password
            )
        except Exception as ex:
            raise serializers.ValidationError(str(ex))

    def update(self, instance, validated_data):
        new_password = self.context.pop("new_password")

        self.validate_user_password(validated_data.get("password"), instance)

        instance.set_password(new_password)
        instance.save()

        return instance


class GenerateThemesSerializer(serializers.Serializer):
    """
    Сериализатор для валидации и генерации тем слайдов.
    """
    # Поле для ввода - тема презентации (только для записи)
    theme = serializers.CharField(
        max_length=1024,
        write_only=True  # Поле используется только на входе, не возвращается в ответе
    )
    # Поле для ввода - количество слайдов (только для записи)
    slides_count = serializers.IntegerField(
        write_only=True,  # Поле используется только на входе
        required=True  # Обязательное поле
    )
    # Поле для вывода - список слайдов (только для чтения)
    # Теперь каждый слайд - объект с text и templateName
    themes = serializers.ListField(
        read_only=True  # Поле только для чтения, не принимается на входе
    )

    def validate(self, attrs: OrderedDict) -> OrderedDict:
        """
        Валидация на уровне всех полей.
        Args:
            attrs: Словарь с валидированными данными
        Returns:
            Проверенные данные
        Raises:
            ValidationError: Если количество слайдов вне диапазона 1-20
        """
        # Получаем количество слайдов из атрибутов
        slides_count = attrs["slides_count"]
        # Проверяем, что количество слайдов в допустимом диапазоне
        if not (1 <= slides_count <= 20):
            raise serializers.ValidationError(
                "The number of slides cannot be less than 1 and more than 20"
            )
        # Возвращаем проверенные данные
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        """
        Генерация слайдов на основе валидированных данных.
        Args:
            validated_data: Проверенные данные с ключами 'theme' и 'slides_count'
        Returns:
            Словарь с ключом 'themes', содержащим список слайдов
        """
        # Извлекаем тему презентации
        theme = validated_data["theme"]
        # Извлекаем количество слайдов
        slides_count = validated_data["slides_count"]
        # Генерируем слайды с помощью обновленной функции
        # Теперь themes - это генератор, выдающий словари {text, templateName}
        themes_generator = generate_slides_with_templates(theme, slides_count)
        # Преобразуем генератор в список (массив объектов)
        themes = list(themes_generator)
        # Возвращаем словарь с результатом
        # Сериализатор автоматически преобразует это в JSON
        return {"themes": themes}


class GenerateSlidesSerializer(serializers.Serializer):
    themes = serializers.ListField(
        write_only=True
    )

    slides = serializers.ListField(
        read_only=True
    )
    engine = serializers.CharField(initial='yandex-art', default='yandex-art', write_only=True)
    model = serializers.CharField(initial='dall-e-3', default='dall-e-3', write_only=True)
    width_ratio = serializers.IntegerField(initial=1, default=1, write_only=True)
    height_ratio = serializers.IntegerField(initial=2, default=2, write_only=True)
    seed = serializers.IntegerField(initial=50, default=50, write_only=True)

    def validate(self, attrs: OrderedDict):
        return attrs

    def create(self, validated_data: dict):
        slides_text = [x for x in generate_slides_text(
            validated_data["themes"]
        )]
        return {"slides": slides_text}


class GetPresentationSerializer(serializers.Serializer):
    id = serializers.IntegerField(
        required=True
    )

    class Meta:
        model = Presentation
        fields = ["id"]

    def validate_user_presentation(self, user, id):
        if not Presentation.objects.filter(user=user, id=id).count():
            raise serializers.ValidationError("Presentation not found!")

    def update(self, instance, validated_data):
        self.validate_user_presentation(instance, validated_data["id"])
        return validated_data


class PaykeeperWebhookSerializer(serializers.Serializer):
    orderid = serializers.UUIDField(required=True)
    status = serializers.CharField(required=True)
    pay_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)


class SharedPresentationRequestSerializer(serializers.Serializer):
    presentation = serializers.SlugRelatedField(
        slug_field='share_link_uid',
        queryset=Presentation.objects.all(),
        read_only=False,
        required=True,
    )


class PresentationSerializer(serializers.ModelSerializer):
    author = serializers.IntegerField(source='user.pk')
    balance = serializers.IntegerField(source='user.balance')

    class Meta:
        model = Presentation
        fields = ('id', 'author', 'json', 'balance')


class UserPresentationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['presentation']


class ScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scope
        fields = ['id', 'title', 'code', 'description', 'visible_in_advantages']


class ExtendedScopeSerializer(serializers.Serializer):
    """Сериализатор для скоупа с дополнительной информацией о тарифах"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    code = serializers.SlugField()
    description = serializers.CharField()
    visible_in_advantages = serializers.BooleanField()
    cheapest_tariff_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    cheapest_tariff_id = serializers.UUIDField(allow_null=True)
    cheapest_tariff_name = serializers.CharField(allow_null=True)
    is_in_current_tariff = serializers.BooleanField()
    current_tariff_price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)

    def to_representation(self, instance):
        # Получаем контекст с пользователем
        user = self.context.get('user')

        cache_key = f'scope_{instance.id}_cheapest_tariff'
        cheapest_tariff = cache.get(cache_key)

        # Находим самый дешёвый активный тариф с этим скоупом (если нет в кеше)
        if cheapest_tariff is None:
            cheapest_tariff = Tariff.objects.filter(
                scopes=instance,
                is_active=True
            ).annotate(
                actual_price=Case(
                    When(special_price__isnull=False, then=F('special_price')),
                    default=F('price'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ).order_by('actual_price').first()
            cache.set(cache_key, cheapest_tariff, 3600)

        # Проверяем, есть ли скоуп в активном тарифе пользователя
        is_in_current_tariff = False
        current_tariff_price = None

        if user and user.tariff and user.tariff.is_active:
            is_in_current_tariff = user.tariff.scopes.filter(id=instance.id).exists()
            # Определяем актуальную цену тарифа пользователя
            current_tariff_price = user.tariff.special_price if user.tariff.special_price is not None else user.tariff.price

        data = {
            'id': instance.id,
            'title': instance.title,
            'code': instance.code,
            'description': instance.description,
            'visible_in_advantages': instance.visible_in_advantages,
            'cheapest_tariff_price': cheapest_tariff.special_price if cheapest_tariff and cheapest_tariff.special_price else (
                cheapest_tariff.price if cheapest_tariff else None),
            'cheapest_tariff_id': str(cheapest_tariff.id) if cheapest_tariff else None,
            'cheapest_tariff_name': cheapest_tariff.name if cheapest_tariff else None,
            'is_in_current_tariff': is_in_current_tariff,
            'current_tariff_price': current_tariff_price,
        }
        return data



class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ['id', 'name']



class TariffSerializer(serializers.ModelSerializer):
    scopes = ScopeSerializer(many=True)
    class Meta:
        model = Tariff
        fields = ['id', 'name', 'price', 'special_price', 'tokens_amount', 'scopes',
                  'extra_text', 'max_slides_count', 'max_imgs_gen_count', 'max_text_gen_count', 'one_token_cost']


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(many=True)
    balance = serializers.FloatField(source='balance.amount', required=False)
    tariff_id = serializers.UUIDField(source='tariff.id', allow_null=True)
    scopes = serializers.SerializerMethodField()
    tariff_price = serializers.DecimalField(source='tariff.price', max_digits=10, decimal_places=2, allow_null=True)
    tariff_special_price = serializers.DecimalField(source='tariff.special_price', max_digits=10, decimal_places=2,allow_null=True)
    tariff_name = serializers.CharField(source='tariff.name', allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role', 'is_active', 'is_staff',
            'balance', 'presentation', 'user_thumb', 'email_verified',
            'tariff_id', 'tariff_name', 'tariff_price', 'tariff_special_price', 'scopes'
        ]

    def get_scopes(self, obj: User):
        # Получаем все скоупы, которые есть в системе (можно кешировать)
        all_scopes = Scope.objects.all()

        # Возвращаем расширенные данные для каждого скоупа
        serializer = ExtendedScopeSerializer(
            all_scopes,
            many=True,
            context={'user': obj}
        )
        return serializer.data


# class ImageSerializer(serializers.Serializer):
#     image = serializers.ImageField()


class ImageSerializer(serializers.Serializer):
    image : serializers.ImageField()
    is_avatar : serializers.BooleanField()

    def validate_image(self, value):
        max_size = 3 * 1024 * 1024  # 3 мегабайта в байтах
        if value.size > max_size:
            raise serializers.ValidationError("Размер изображения не должен превышать 3 мегабайта.")

        valid_extensions = ['.jpg', '.jpeg', '.png']
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError("Допустимы только изображения форматов: jpg, jpeg, png.")

        return value


class BalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceHistory
        fields = ['amount_change', 'change_type', 'change_reason']

    def validate(self, data):
        user = self.context['request'].user
        balance = user.balance  # Предполагается, что у пользователя есть связь с балансом
        amount_change = data.get('amount_change')
        change_type = data.get('change_type')

        if change_type == BalanceHistory.ChangeType.DECREASE and balance.amount < amount_change:
            raise ValidationError("Недостаточно средств на балансе.")

        return data


class PromoCodeApplySerializer(serializers.Serializer):
    promo_code = serializers.CharField(max_length=255, required=True)

    def validate_promo_code(self, value):
        try:
            promo_code = PromoCode.objects.get(code=value, is_active=True)
        except PromoCode.DoesNotExist:
            raise serializers.ValidationError("Промокод не найден или неактивен.")

        # Проверка срока действия
        if promo_code.expiration_date < date.today():
            raise serializers.ValidationError("Промокод истёк.")

        # Сохранение промокода для использования позже
        self.promo_code = promo_code
        return value

    def save(self, user):
        promo_code = self.promo_code

        # Проверка одноразового использования
        # breakpoint()
        if promo_code.usage_type == PromoCode.SINGLE_USE:
            if PromoCodeUsage.objects.filter(promo_code=promo_code, user=user).exists():
                raise serializers.ValidationError("Этот промокод уже был использован вами.")

        # Проверка лимита использования для многоразового промокода
        if promo_code.usage_type == PromoCode.MULTI_USE and promo_code.usage_limit <= 0:
            raise serializers.ValidationError("Лимит использования этого промокода исчерпан.")

        # Применение промокода (пример: добавление токенов пользователю)
        if hasattr(user, 'balance'):
            user.balance.amount = F('amount') + promo_code.token_amount
            user.balance.save()
            BalanceHistory.objects.create(
                amount_change=promo_code.token_amount,
                change_type=BalanceHistory.ChangeType.INCREASE,
                change_reason=BalanceHistory.Reason.PROMOTIONAL_CODE,
                balance=user.balance,
            )

        # Создание записи об использовании
        PromoCodeUsage.objects.create(user=user, promo_code=promo_code)

        # Уменьшение лимита использования, если это многоразовый промокод
        if promo_code.usage_type == PromoCode.MULTI_USE:
            promo_code.usage_limit = F('usage_limit') - 1
            promo_code.save()

        return promo_code


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    email = serializers.EmailField()
    new_password = serializers.CharField()


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()
