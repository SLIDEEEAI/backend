from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):

    def create_user_object(self, username, email, password):
        if username is None:
            raise TypeError('Users must have a username.')

        if email is None:
            raise TypeError('Users must have an email address.')

        user = self.model(
            username=username, email=self.normalize_email(email)
        )

        user.set_password(password)
        user.save()

        return user

    def create_user(self, username, email, password, role):

        user = self.create_user_object(
            username=username, email=email, password=password
        )

        user.save()
        user.role.set(role)
        user.save()

        return user

    def create_superuser(self, username, email, password):
        if password is None:
            raise TypeError('Superusers must have a password.')

        if username is None:
            raise TypeError('Users must have a username.')

        if email is None:
            raise TypeError('Users must have an email address.')

        user = self.create_user_object(username, email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        return user
