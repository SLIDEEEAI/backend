from django.db import models


class Config(models.Model):
    referral_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    bonus_to_new_users = models.DecimalField(max_digits=10, decimal_places=2, default=1000)

    telegram_group_joined_promocode_token_amount = models.IntegerField(default=100_000)
    telegram_admins_id = models.JSONField(default=[])
    telegram_group_id = models.CharField(default='')
    telegram_bot_apikey = models.CharField(default='')


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
