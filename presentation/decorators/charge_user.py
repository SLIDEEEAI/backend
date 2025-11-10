from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError

from presentation.models import BalanceHistory
from presentation.service_modules.balance_service import BalanceService


def charge_user(amount, reason, wrap_response=True):
    """
    Декоратор для списания средств с пользователем после успешного выполнения view

    Args:
        amount: сумма списания
        reason: причина из BalanceHistory.Reason
        wrap_response: оборачивать ли ответ в расширенную структуру
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            # Проверяем достаточно ли средств ДО выполнения операции
            if not BalanceService.has_sufficient_funds(request.user, amount):
                return Response(
                    {
                        "error": "Недостаточно средств на балансе",
                        "required_amount": amount,
                        "current_balance": BalanceService.get_user_balance(request.user).amount
                    },
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )

            initial_balance = BalanceService.get_user_balance(request.user).amount

            # Выполняем основную операцию
            response = view_func(self, request, *args, **kwargs)

            # Если операция успешна (статус 2xx), списываем средства
            if 200 <= response.status_code < 300:
                try:
                    BalanceService.decrease_balance(
                        user=request.user,
                        amount=amount,
                        reason=reason
                    )

                    updated_balance = BalanceService.get_user_balance(request.user)

                    if wrap_response:
                        original_data = response.data

                        extended_response = {
                            "success": True,
                            "transaction": {
                                "charged_amount": amount,
                                "previous_balance": initial_balance,
                                "new_balance": updated_balance.amount,
                                "reason": BalanceHistory.Reason(reason).label,
                                "transaction_message": "Средства успешно списаны"
                            },
                            "result": original_data
                        }

                        response.data = extended_response
                    else:
                        # Добавляем информацию о транзакции в существующий ответ
                        if isinstance(response.data, dict):
                            response.data['transaction_info'] = {
                                'charged': str(amount),
                                'balance_after': str(updated_balance.amount)
                            }

                except ValidationError as e:
                    print(f"Balance charge failed: {e}")
                    # Обработка ошибки списания...

            return response

        return _wrapped_view

    return decorator