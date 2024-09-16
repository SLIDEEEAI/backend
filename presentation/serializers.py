from django.contrib.auth import authenticate, password_validation
from django.forms.models import model_to_dict

from rest_framework import serializers
from collections import OrderedDict

from .models import User, Roles, Presentation

from .services import generate_slides_theme, generate_slides_text

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework import serializers
from .models import User

class PaykeeperWebhookSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    amount = serializers.IntegerField(required=True)

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this ID does not exist.")
        return value
    
    
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
    role = serializers.IntegerField(write_only=True)
    token = serializers.DictField(read_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'role', 'password', 'token']

    def validate(self, attrs: OrderedDict):
        if attrs["role"] not in [x.id for x in Roles.objects.all()]:
            raise serializers.ValidationError(
                "Available roles for registration - {}".format(
                    ', '.join([str(x.id) for x in Roles.objects.all()])
                )
            )
        return attrs

    def create(self, validated_data):
        role = validated_data.pop("role")
        role = Roles.objects.get(id=role)
        validated_data.update({"role": role})

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
