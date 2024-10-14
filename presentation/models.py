from rest_framework_simplejwt.tokens import RefreshToken

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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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