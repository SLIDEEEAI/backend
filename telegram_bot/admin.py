from django.contrib import admin
from .models import Command, TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id')


@admin.register(Command)
class CommandAdmin(admin.ModelAdmin):
    list_display = ('title', 'command', 'signal', 'button_text', 'next_message')
    search_fields = ('command', 'response')
    list_filter = ('signal',)

    #
    # def formfield_for_choice_field(self, db_field, request, **kwargs):
    #     if db_field.name == 'signal':
    #         object_id = request.resolver_match.kwargs.get('object_id')
    #         used_signals = Command.objects.exclude(pk=object_id).exclude(signal__isnull=True).values_list('signal', flat=True)
    #
    #         choices = [
    #             (value, label)
    #             for value, label in db_field.choices
    #             if value not in used_signals
    #         ]
    #         kwargs['choices'] = [('', '---------')] + choices

        # return super().formfield_for_choice_field(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)
