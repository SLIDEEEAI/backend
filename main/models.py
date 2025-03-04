from django.db import models


class Config(models.Model):
    referral_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    bonus_to_new_users = models.DecimalField(max_digits=10, decimal_places=2, default=1000)

    class Meta:
        verbose_name = "Config"
        verbose_name_plural = "Configs"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_instance(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
