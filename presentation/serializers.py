import os

from django.contrib.auth import authenticate, password_validation

from django.core.exceptions import ValidationError

from django.db.models import F

from django.forms.models import model_to_dict

from collections import OrderedDict

from .models import Roles, Presentation, Tariff, BalanceHistory, PromoCode, PromoCodeUsage, Scope
from rest_framework.serializers import ValidationError

from .services import generate_slides_theme, generate_slides_text

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
    theme = serializers.CharField(
        max_length=1024, write_only=True
    )

    slides_count = serializers.IntegerField(
        write_only=True, required=True
    )

    themes = serializers.ListField(
        read_only=True
    )

    def validate(self, attrs: OrderedDict):
        slides_count = attrs["slides_count"]
        if not (slides_count < 21 and slides_count > 0):
            raise serializers.ValidationError(
                "The number of slides cannot be less than 1 and more than 20"
            )
        return attrs

    def create(self, validated_data: dict):
        theme = validated_data["theme"]
        slides_count = validated_data["slides_count"]
        themes = [x for x in generate_slides_theme(theme, slides_count)]

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
        fields = ['id', 'title', 'token_price']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ['id', 'name']



class TariffSerializer(serializers.ModelSerializer):
    scopes = ScopeSerializer(many=True)
    class Meta:
        model = Tariff
        fields = ['id', 'name', 'price', 'presentation_count', 'scopes']


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(many=True)
    balance = serializers.FloatField(source='balance.amount', required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'is_active', 'is_staff', 'balance', 'presentation', 'user_thumb', 'email_verified']


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
