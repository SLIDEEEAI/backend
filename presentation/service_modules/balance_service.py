# service_modules/balance_service.py
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from presentation.models import Balance, BalanceHistory


class BalanceService:
    @staticmethod
    @transaction.atomic
    def increase_balance(user, amount, reason):
        """Увеличить баланс пользователя"""
        if amount <= 0:
            raise ValidationError("Amount must be positive for increase")

        return BalanceService._change_balance(
            user, amount, BalanceHistory.ChangeType.INCREASE, reason
        )

    @staticmethod
    @transaction.atomic
    def decrease_balance(user, amount, reason):
        """Уменьшить баланс пользователя"""
        if amount <= 0:
            raise ValidationError("Amount must be positive for decrease")

        # Проверяем достаточно ли средств
        if not BalanceService.has_sufficient_funds(user, amount):
            raise ValidationError("Insufficient funds")

        return BalanceService._change_balance(
            user, amount, BalanceHistory.ChangeType.DECREASE, reason
        )

    @staticmethod
    def _change_balance(user, amount, change_type, reason):
        """Общая логика изменения баланса"""
        # Изменяем баланс
        balance = user.balance
        if change_type == BalanceHistory.ChangeType.INCREASE:
            balance.amount += Decimal(amount)
        else:
            balance.amount -= Decimal(amount)

        balance.save()

        # Создаем запись в истории
        balance_history = BalanceHistory.objects.create(
            amount_change=amount,
            change_type=change_type,
            change_reason=reason,
            balance=balance,
        )

        return balance_history

    @staticmethod
    def has_sufficient_funds(user, amount):
        """Проверить, достаточно ли средств у пользователя"""
        try:
            # Проверяем существование баланса
            if not hasattr(user, 'balance') or user.balance is None:
                return False
            return user.balance.amount >= Decimal(amount)
        except Balance.DoesNotExist:
            return False

    @staticmethod
    def get_user_balance(user):
        """Получить баланс пользователя (создает если не существует)"""
        # balance, created = Balance.objects.get_or_create(user=user)
        return user.balance