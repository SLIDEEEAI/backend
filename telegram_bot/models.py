import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now

from main.models import Config
from presentation.models import PromoCode
from telegram_bot.signals import user_joined_to_group


class TelegramUser(models.Model):
    telegram_id = models.CharField(max_length=256)
    username = models.CharField(max_length=256, default=None, null=True)
    fullname = models.CharField(max_length=256, default=None, null=True)
    is_group_member = models.BooleanField(default=False)
    join_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    promocode = models.ForeignKey('presentation.PromoCode', null=True, blank=True, on_delete=models.SET_NULL)
    promocode_received = models.BooleanField(default=False)

    def apply_promocode(self):
        code = PromoCode.objects.create(
            code=str(uuid.uuid4()).split('-')[0],
            usage_type=PromoCode.SINGLE_USE,
            expiration_date=now()+timedelta(days=365),
            can_sum=False,
            token_amount=Config.get_instance().telegram_group_joined_promocode_token_amount,
        )
        self.promocode = code
        self.save(update_fields=['promocode'])


class Command(models.Model):
    class Signals(models.TextChoices):
        USER_JOIN_GROUP = 'user_join', 'Когда пользователь вступил в группу'
        USER_LEFT_GROUP = 'user_left', 'Когда пользователь покинул группу'
        USER_START_USE_BOT = 'user_start_use_bot', 'Когда пользователь начал использовать бота'

    class OnlyFor(models.TextChoices):
        NOT_JOINED_TO_GROUP = 'not_group_joined', 'Только для тех, кто НЕ вступил в группу'
        PROMOCODE_NOT_RECEIVED = 'not_code_received', 'Только для тех, кто НЕ получил промокод'
        JOINED_TO_GROUP = 'group_joined', 'Только для тех, кто вступил в группу'
        PROMOCODE_RECEIVED = 'code_received', 'Только для тех, кто получил промокод'

    class Actions(models.TextChoices):
        CHECK_USER_JOINED_TO_GROUP = 'ck_user_group_joined', 'Запустить проверку вступил ли юзер в группу'
    title = models.CharField(max_length=255, verbose_name='Название инструкции', help_text='Это не будет играть роли при исполнения инструкции')
    command = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Команда или текст',
        help_text='Команда или сообщение, по которому будет отправлен ответ. Например, "start" или "привет".'
    )

    signal = models.CharField(
        max_length=56,
        null=True,
        blank=True,
        choices=Signals.choices,
        verbose_name='Сигнал',
        help_text='Автоматический сигнал, при котором будет отправлено сообщение.'
    )

    only_for = models.CharField(
        max_length=56,
        null=True,
        blank=True,
        choices=OnlyFor.choices,
        verbose_name='Ограничение по пользователю',
        help_text='Позволяет отправлять сообщение только определённой категории пользователей.'
    )

    action = models.CharField(
        max_length=56,
        null=True,
        blank=True,
        choices=Actions.choices,
        verbose_name='Доп. функция',
        help_text='Запуск дополнительной функции до выполнение инструкции. Это может быть проверка состоит ли юзер в группе'
    )

    response = models.TextField(
        verbose_name='Текст сообщения',
        help_text=(
            'Текст, который будет отправлен пользователю. '
            'Доступные переменные:<br>'
            '<strong>{username}</strong> — Юзернейм Telegram-пользователя<br>'
            '<strong>{fullname}</strong> — Имя и Фамилия пользователя<br>'
            '<strong>{id}</strong> — Telegram ID пользователя<br>'
            '<strong>{promocode_received}</strong> — "получен"/"не получен" статус по промокоду<br>'
            '<strong>{promocode}</strong> — сам промокод<br>'
            '<strong>{amount}</strong> — количество кредитов в промокоде'
        ),
        null=True,
        blank=True,
    )

    button_text = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Название кнопки',
        help_text='Текст, отображаемый на кнопке под сообщением.'
    )

    button_link = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name='Действие кнопки',
        help_text=(
            'Ссылка, команда или текст. '
            'Если указана команда или текст, и они обрабатываются инструкцией, будет выполнено соответствующее действие.'
        )
    )

    next_message = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_commands',
        verbose_name='Следующее сообщение',
        help_text='Следующее сообщение, которое будет отправлено после текущего.'
    )
    priority = models.SmallIntegerField(default=0)
    finish = models.BooleanField('Закончить дальнейшее выполнение последующих инструкции', default=False)

    class Meta:
        verbose_name = 'Инструкция'
        verbose_name_plural = 'Инструкции'
        ordering = ['-priority']

    def __str__(self):
        return self.title

    def call_action(self, user):
        funcs = {
            self.Actions.CHECK_USER_JOINED_TO_GROUP.value: Command._check_user_joined_to_group,
        }
        return funcs[self.action](self, user)


    def _check_user_joined_to_group(self, user: TelegramUser):
        from telegram_bot.telegram_core import is_user_in_group

        is_member = is_user_in_group(user.telegram_id, Config.get_instance().telegram_group_id)
        if is_member and not user.is_group_member:
            user_joined_to_group.send(sender=self.__class__, user=user)
        user.is_group_member = is_member
        user.save(update_fields=['is_group_member'])

    def clean(self):
        if self.button_text and not self.button_link:
            raise ValidationError({'button_link': 'Если указана кнопка, необходимо указать ссылку на неё.'})

        if self.button_link and not self.button_text:
            raise ValidationError(
                {'button_text': 'Если указана ссылка на кнопку, необходимо указать текст кнопки.'})

        if self.next_message:
            if self.pk == self.next_message.pk:
                raise ValidationError({'next_message': 'Цепочка сообщений не может ссылаться на само себя.'})

            visited = set()
            current = self.next_message
            while current:
                if current.pk in visited:
                    raise ValidationError({'next_message': 'Цепочка сообщений не может быть циклической.'})
                visited.add(current.pk)
                current = current.next_message