import hashlib
import os

from django.conf import settings
from django.core.exceptions import ValidationError

from django.db.models import F
from datetime import datetime

from django.db.transaction import atomic
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import AccessToken

from presentation.decorators.rate_limit_with_timeout import rate_limit_with_timeout
from main.models import Config
from presentation.models import Presentation, Transaction, Tariff, BalanceHistory, Balance, PromoCode, \
    EmailVerificationToken, PasswordResetToken, Roles
from source.settings import PAYKEEPER_USER, PAYKEEPER_PASSWORD, SERVER_PAYKEEPER, PAYKEEPER_POST_SECRET_WORD
from django.shortcuts import get_object_or_404
from django.db import transaction as atomic_transaction
from rest_framework import generics, serializers
from decimal import Decimal

from .serializers import (
    RegistrationSerializer,
    ChangePasswordSerializer,
    GenerateThemesSerializer,
    GenerateSlidesSerializer,
    GPTRequestSerializer,
    GetPresentationSerializer,
    PaykeeperWebhookSerializer,

    ImageSerializer,

    TariffSerializer,
    UserSerializer,
    BalanceHistorySerializer,
    PromoCodeApplySerializer,
    PresentationSerializer,
    SharedPresentationRequestSerializer, ResetPasswordSerializer, VerifyEmailSerializer, RoleSerializer,

)
from .service_modules.balance_service import BalanceService
from .service_modules.presentations_service import PresentationsService

from .services import (
    generate_json_object,
    generate_images_from_list,
    export_presentation,
    generate_short_text,
    generate_long_text,
    generate_bullet_points,
    generate_image_with_caption,
    generate_quote,
    generate_chart_data,
    generate_questions,
    generate_slide_title,
    generate_slide_heading,
    generate_custom_request,
    send_verification_email,
    send_reset_password_email,
)

import base64
import json

from django.http import JsonResponse
from .models import User
from .trottles import EnterPasswordReset, RequestToResetPassword


class PaykeeperWebhookView(APIView):
    @atomic_transaction.atomic
    def post(self, request):

        # Пример запроса от Paykeeper
        # {"id": "240711111", "sum": "899.00", "clientid": "8", "orderid": "a5252849-d8d9-4cd9-a596-f67db8bc2c50",
        #  "key": "154d23e4da2f9938a1fbed64bb2f5908", "pk_hostname": "https://slideee.server.paykeeper.ru",
        #  "ps_id": "127", "client_email": "is@mail.ru", "client_phone": "",
        #  "service_name": "\u041f\u043e\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u0435 \u0431\u0430\u043b\u0430\u043d\u0441\u0430 SlideeeAI",
        #  "card_number": "5100********3333", "card_holder": "Test Gateway", "card_expiry": "03/30",
        #  "obtain_datetime": "2025-12-04 00:19:25", "RRN": "17647967655130", "APPROVAL_CODE": "",
        #  "invoice_id": "20251204001844212"}

        file_path = os.path.join(settings.MEDIA_ROOT, "last_post_payment_webhook_request_data.txt")
        with open(file_path, 'w+') as file:
            file.write(json.dumps(request.data))

        # serializer = PaykeeperWebhookSerializer(data=request.data, many=True)

        # if not serializer.is_valid():
        #     return self.create_error_response('Invalid data', serializer.errors)

        request_id = request.data.get('id')
        sum_amount = request.data.get('sum')
        client_id = request.data.get('clientid')
        order_id = request.data.get('orderid')
        key = request.data.get('key')

        # request_ok = self.validate_paykeeper_request(request_id, sum_amount, client_id, order_id, key)

        # if not request_ok:
        #     file_path = os.path.join(settings.MEDIA_ROOT, "Invalid_Paykeeper_request_hash.txt")
        #     with open(file_path, 'w+') as file:
        #         file.write(str(request_ok))
        #     return self.create_error_response('Invalid Paykeeper request hash', {'orderid': order_id})

        transaction = self.get_transaction(order_id)
        if transaction.status == Transaction.Statuses.COMPLETED:
            return self.create_error_response('The transaction has already been completed', {'orderid': order_id})

        if not transaction:
            return self.create_error_response('Transaction not found', {'orderid': order_id})

        self.complete_transaction(transaction)

        return JsonResponse({'status': 'success'}, status=200)

    def get_transaction(self, order_id):
        """Helper method to retrieve the transaction based on the order_id."""
        return get_object_or_404(Transaction, order_id=order_id)

    def validate_paykeeper_request(self, id_param, sum_param, client_id_param, order_id_param, key):
        try:
            file_path = os.path.join(settings.MEDIA_ROOT, "hashes_inside.txt")
            with open(file_path, 'w+') as file:
                file.write("hashes_inside")

            s = id_param + sum_param + client_id_param + order_id_param + "NXXG5u3l)SrLqKXsZo"

            file_path = os.path.join(settings.MEDIA_ROOT, "s.txt")
            with open(file_path, 'w+') as file:
                file.write(s)

            hash_result = hashlib.md5(s.encode())

            file_path = os.path.join(settings.MEDIA_ROOT, "hashes_results.txt")
            with open(file_path, 'w+') as file:
                file.write("key: " + key + "\nhash_result: " + hash_result.hexdigest())

            return key == hash_result.hexdigest()
        except Exception as e:
            file_path = os.path.join(settings.MEDIA_ROOT, "validate_paykeeper_request_Exception.txt")
            with open(file_path, 'w+') as file:
                file.write(str(e))

    def validate_amount(self, transaction, amount):
        """Check if the received amount matches the transaction amount."""
        return amount == transaction.amount

    def complete_transaction(self, transaction):
        """Complete the transaction, update user's balance and presentation count."""
        transaction.status = Transaction.Statuses.COMPLETED
        # transaction.user.balance.amount = F('balance') + transaction.amount

        tariff = Tariff.objects.filter(price=transaction.amount).first()
        if tariff:
            BalanceService.increase_balance(transaction.user, tariff.tokens_amount, BalanceHistory.Reason.TOP_UP)
            # transaction.user.balance = F('presentation') + tariff.tokens_amount
            if tariff.price > transaction.user.tariff.price:
                transaction.user.tariff = tariff

        transaction.user.save()
        transaction.save()

    def create_error_response(self, message, details=None, status=400):
        """Helper method to create structured error responses."""
        error_response = {'status': 'error', 'message': message}
        if details:
            error_response['details'] = details
        return JsonResponse(error_response, status=status)

class CreatePaymentLinkView(APIView):

    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        try:
            user = request.user
            # user = User.objects.all().last()

            transaction_uuid = uuid.uuid4()
            amount = request.data.get('pay_amount')

            token = self.get_paykeeper_token()

            payment_data = self.build_payment_data(user, transaction_uuid, amount)
            payment_link = self.create_invoice_link(payment_data, token)

            self.save_transaction(transaction_uuid, user, amount, payment_link)

            return JsonResponse({'link': payment_link}, status=200)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def get_paykeeper_token(self):
        """Fetches the token from PayKeeper."""
        headers = self.build_auth_headers()

        uri = "/info/settings/token/"
        response = requests.get(SERVER_PAYKEEPER + uri, headers=headers)
        php_array = response.json()

        token = php_array.get('token')
        if not token:
            raise ValueError('Token not found')

        return token

    def build_auth_headers(self):
        """Builds authorization headers for PayKeeper requests."""
        credentials = f"{PAYKEEPER_USER}:{PAYKEEPER_PASSWORD}"
        base64_credentials = base64.b64encode(credentials.encode()).decode('utf-8')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {base64_credentials}'
        }
        return headers

    def build_payment_data(self, user, transaction_uuid, amount):
        """Builds payment data for PayKeeper request."""
        return {
            "pay_amount": amount,
            "clientid": user.id,
            "orderid": transaction_uuid,
            "client_email": user.email,
            "service_name": 'Пополнение баланса SlideeeAI',
        }

    def create_invoice_link(self, payment_data, token):
        """Creates an invoice link using PayKeeper API."""
        headers = self.build_auth_headers()
        uri = "/change/invoice/preview/"

        payload = {**payment_data, 'token': token}
        response = requests.post(SERVER_PAYKEEPER + uri, headers=headers, data=payload)
        response_data = response.json()

        invoice_id = response_data.get('invoice_id')
        if not invoice_id:
            raise ValueError('Invoice ID not found')

        return f"{SERVER_PAYKEEPER}/bill/{invoice_id}/"

    def save_transaction(self, transaction_uuid, user, amount, payment_link):
        """Saves the transaction to the database."""
        Transaction.objects.create(
            uuid=transaction_uuid,
            user=user,
            order_id=transaction_uuid,
            amount=amount,
            currency='RUB',
            status=Transaction.Statuses.WAITING_PAYMENT,
            payment_url=payment_link,
        )

class DecrementPresentationView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        user = request.user

        if user.presentation < 1:
            return Response({'error': 'User does not have enough presentations left.'}, status=status.HTTP_400_BAD_REQUEST)

        user.presentation = F('presentation') - 1
        user.save()

        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class GPTRequestView(APIView):
    def post(self, request):
        serializer = GPTRequestSerializer(data=request.data)
        if serializer.is_valid():
            # Получаем запрос к GPT
            gpt_request = serializer.validated_data.get('gpt_request')

            # Здесь обрабатываем запрос к GPT
            # В данном случае просто возвращаем его обратно в ответе

            # gpt_response = f"Привет! Вы ввели запрос: '{gpt_request}' и отправили его на обработку GPT."
            gpt_response = generate_custom_request(gpt_request)

            # Возвращаем успешный ответ с результатом обработки
            return Response({"gpt_response": gpt_response}, status=status.HTTP_200_OK)
        else:
            # Если данные некорректны, возвращаем ошибку
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetUserBalanceView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    serializer_class = GetPresentationSerializer

    def post(self, request):
        if request:
            user = User.objects.filter(id = request.user.id).first()
            if user:
                return Response(
                    {
                        "balance" : user.balance.amount
                    },
                    status=status.HTTP_201_CREATED
                )
        return Response(
            data="Presentation not found!",
            status=400
        )
    

class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        # Аутентификация пользователя
        user = authenticate(username=username, password=password)
        
        if user:
            login(request, user)  # Логиним пользователя

            # Сохраняем айди пользователя в локальное хранилище
            request.session['user_id'] = user.id

            return Response({'detail': 'Authenticated'}, status=200)
        else:
            return Response({'error': 'Invalid credentials'}, status=400)

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access_token = AccessToken(response.data['access'])
            user_id = access_token.payload.get('user_id')
            response.data['user_id'] = user_id
        return response

class GenerateShortTextView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        max_tokens = request.data.get('max_tokens', 50)
        short_text = generate_short_text(presentation_theme, max_tokens)
        return Response({'short_text': short_text}, status=status.HTTP_200_OK)

class GenerateLongTextView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        max_tokens = request.data.get('max_tokens', 500)
        long_text = generate_long_text(presentation_theme, max_tokens)
        return Response({'long_text': long_text, "tokens" :  max_tokens}, status=status.HTTP_200_OK)

class GenerateBulletPointsView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        max_items = request.data.get('max_items', 5)
        bullet_points = generate_bullet_points(presentation_theme, max_items)
        return Response({'bullet_points': bullet_points}, status=status.HTTP_200_OK)

class GenerateImageWithCaptionView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        engine = request.data.get('engine', 'yandex')
        model = request.data.get('model', 'yandex-art')
        width_ratio = request.data.get('presentation_theme', 1)
        height_ratio = request.data.get('presentation_theme', 2)
        seed = request.data.get('presentation_theme', 50)
        image_url, caption = generate_image_with_caption(presentation_theme, engine=engine, model=model, width_ratio=width_ratio, height_ratio=height_ratio, seed=seed)
        return Response({'image_url': image_url, 'caption': caption}, status=status.HTTP_200_OK)

class GenerateQuoteView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        quote = generate_quote(presentation_theme)
        return Response({'quote': quote}, status=status.HTTP_200_OK)

class GenerateChartDataView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        chart_data = generate_chart_data(presentation_theme)
        return Response({'chart_data': chart_data}, status=status.HTTP_200_OK)

class GenerateQuestionsView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        max_questions = request.data.get('max_questions', 3)
        questions = generate_questions(presentation_theme, max_questions)
        return Response({'questions': questions}, status=status.HTTP_200_OK)

class GenerateSlideTitleView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        slide_title = generate_slide_title(presentation_theme)
        return Response({'slide_title': slide_title}, status=status.HTTP_200_OK)

class GenerateSlideHeadingView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        slide_heading = generate_slide_heading(presentation_theme)
        return Response({'slide_heading': slide_heading}, status=status.HTTP_200_OK)


from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
import requests
import uuid

from .models import GeneratedImage
from .services import generate_images

class GenerateImagesView(APIView):
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        num_images = request.data.get('num_images', 1)
        engine = request.data.get('engine', 'yandex')
        model = request.data.get('model', 'yandex-art')
        width_ratio = request.data.get('width_ratio', 1)
        height_ratio = request.data.get('width_ratio', 2)
        seed = request.data.get('width_ratio', 50)

        image_urls = generate_images(presentation_theme, num_images=num_images, engine=engine, model=model, width_ratio=width_ratio, height_ratio=height_ratio, seed=seed)

        saved_images = []
        for url in image_urls:

            # Загружаем изображение
            response = requests.get(url)
            if response.status_code == 200:
                # Генерируем уникальное имя файла
                file_name = f"{uuid.uuid4()}.jpg"

                # Сохраняем изображение
                path = default_storage.save(f"generated_images/{file_name}", ContentFile(response.content))

                # Создаем запись в базе данных
                image = GeneratedImage.objects.create(
                    theme=presentation_theme,
                    image=path
                )

                saved_images.append({
                    'id': image.id,
                    'url': request.build_absolute_uri(image.image.url)
                })

        return Response({'images': saved_images}, status=status.HTTP_200_OK)
#старые


class RegistrationView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = RegistrationSerializer

    @swagger_auto_schema(request_body=RegistrationSerializer)
    @atomic
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_data = serializer.save()
        referrer: User = serializer.validated_data.get('referral_user')
        promocode: PromoCode = serializer.validated_data.get('promocode')

        # Установите баланс пользователя
        user = User.objects.get(email=user_data['email'])
        balance = Balance.objects.create(amount=Config.get_instance().bonus_to_new_users)
        user.balance = balance
        BalanceHistory.objects.create(
            amount_change=Config.get_instance().bonus_to_new_users,
            change_type=BalanceHistory.ChangeType.INCREASE,
            change_reason=BalanceHistory.Reason.BONUS_REGISTRATION,
            balance=balance,
        )
        if referrer:
            user.referrer = referrer
            referrer.balance.amount = F('amount') + Config.get_instance().referral_bonus
            referrer.balance.save(update_fields=['amount'])
            BalanceHistory.objects.create(
                amount_change=Config.get_instance().referral_bonus,
                change_type=BalanceHistory.ChangeType.INCREASE,
                change_reason=BalanceHistory.Reason.REFERRAL_TOP_UP,
                balance=referrer.balance,
            )
        user.save()
        response_data = {
            'user_id': user.id,  # Возвращаем идентификатор пользователя вместе с ответом
            'access': user_data['token']['access'],
            'refresh': user_data['token']['refresh'],
        }
        if promocode:
            promocode_serializer = PromoCodeApplySerializer(data={'promo_code': promocode.code})
            promocode_serializer.is_valid(raise_exception=True)
            promocode_serializer.save(user)
        send_verification_email(user)
        return Response(response_data, status=status.HTTP_201_CREATED)


class ResendVerificationEmailView(APIView):
    permission_classes = (IsAuthenticated,)

    retry_after = 120

    @swagger_auto_schema(
        responses={
            200: "Письмо с верификацией отправлено",
            400: "Аккаунт уже верифицирован"
        }
    )
    @atomic
    @rate_limit_with_timeout(lambda request: f"resend_verification:{request.user.id}", rate_seconds=retry_after)
    def post(self, request, *args, **kwargs):
        user = request.user

        # Проверяем, не верифицирован ли пользователь уже
        if user.email_verified:
            return Response(
                {"error": "Аккаунт уже верифицирован"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Отправляем письмо с верификацией
        send_verification_email(user)

        return Response(
            {"message": "Письмо с верификацией отправлено на ваш email", "retry_after" : self.retry_after},
            status=status.HTTP_200_OK
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=VerifyEmailSerializer)
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        verification_token = get_object_or_404(EmailVerificationToken, token=token)
        verification_token.user.email_verified = True
        verification_token.user.save()
        verification_token.delete()

        return Response({"message": "Email successfully verified"}, status=status.HTTP_200_OK)


class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = (RequestToResetPassword, )

    def post(self, request):
        user = User.objects.filter(email=request.data.get('email')).first()
        if user is None:
            return Response(
                {"error": "user is not found"},
                status=status.HTTP_403_FORBIDDEN
            )
        send_reset_password_email(user)
        return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = (EnterPasswordReset, )

    @swagger_auto_schema(request_body=ResetPasswordSerializer)
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data["token"]
            email = serializer.validated_data["email"]
            new_password = serializer.validated_data["new_password"]
            reset_token = get_object_or_404(PasswordResetToken, token=token, user__email=email)
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            reset_token.delete()
            return Response({"message": "Password successfully reset"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        user = User.objects.filter(email=request.user).first()

        if user is None:
            return Response(
                {"error": "user is not found"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.serializer_class(
            instance=user, data=request.data
        )

        serializer.context.update({"new_password": request.data.get("new_password")})

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_200_OK)


class GenerateThemesView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    serializer_class = GenerateThemesSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class GenerateSlidesView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    serializer_class = GenerateSlidesSerializer

    def post(self, request):
        serializer: GenerateSlidesSerializer = self.serializer_class(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Получаем пользователя
        user = request.user

        # Проверяем, достаточно ли у пользователя средств для создания презентации
        if user.balance.amount < 10:
            return Response(
                {"error": "Insufficient funds"},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )

        # Списываем средства
        user.balance.amount -= 10
        user.save()

        # Создаем презентацию
        presentation = Presentation.objects.create(
            user=user,
            json=generate_json_object(
                request.data["themes"],
                serializer.data["slides"],
                generate_images_from_list(
                    serializer.data["slides"],
                    engine=serializer.data.get('engine'),
                    model=serializer.data.get('model'),
                    width_ratio=serializer.data.get('width_ratio'),
                    height_ratio=serializer.data.get('height_ratio'),
                    seed=serializer.data.get('seed'),
                )
            )
        )

        return Response(
            {
                "id": presentation.id,
                "author": presentation.user.id,
                "json": json.loads(presentation.json)
            },
            status=status.HTTP_201_CREATED
        )


class GetPresentationView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    serializer_class = GetPresentationSerializer

    @swagger_auto_schema(
        operation_summary="Получение презентации",
        operation_description="Возвращает данные о презентации по её ID, если пользователь является её владельцем.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["id"],
            properties={
                "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID презентации"),
            },
        ),
        responses={
            201: openapi.Response(
                description="Успешный ответ",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID презентации"),
                        "author": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID автора"),
                        "json": openapi.Schema(type=openapi.TYPE_OBJECT, description="JSON-содержимое презентации"),
                        "shared_uid": openapi.Schema(type=openapi.TYPE_STRING,
                                                     description="Уникальный идентификатор ссылки на презентацию"),
                        "balance": openapi.Schema(type=openapi.TYPE_NUMBER, description="Баланс пользователя"),
                    },
                ),
            ),
            400: openapi.Response(description="Презентация не найдена"),
            403: openapi.Response(description="Доступ к чужому проекту запрещён"),
        },
    )
    def post(self, request):
        if request and request.data["id"]:
            presentation = Presentation.objects.filter(id=request.data["id"]).first()
            if presentation:

                # проверка на подлинность проекта
                if presentation.user.id != request.user.id:
                    return Response(
                        data="Access to someone else's project is denied.",
                        status=403
                    )

                return Response(
                    {
                        "id": presentation.id,
                        "author": presentation.user.id,
                        "json": json.loads(presentation.json),
                        "shared_uid": str(presentation.share_link_uid),
                        # -- uncomment
                        # "balance" : presentation.user.balance
                    },
                    status=status.HTTP_201_CREATED
                )
        return Response(
            data="Presentation not found!",
            status=400
        )


class GetPresentationSharedView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (AllowAny,)
    queryset = Presentation.objects.select_related('user')
    serializer_class = PresentationSerializer

    @swagger_auto_schema(request_body=SharedPresentationRequestSerializer)
    def post(self, request):
        serializer = SharedPresentationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(self.serializer_class(serializer.validated_data['presentation']).data)


class SavePresentationView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        if request and request.data["id"]:
            presentation = Presentation.objects.filter(id=request.data["id"]).first()
            if presentation:
                presentation.json = json.dumps(request.data["json"])
                presentation.save()

                return Response(
                    data='saved',
                    status=status.HTTP_200_OK
                )
        return Response(
            data="Presentation not found!",
            status=400
        )


class DeletePresentationView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        if request and request.data["id"]:
            presentation = Presentation.objects.filter(id=request.data["id"]).first()
            if presentation:
                presentation.delete()

                return Response(
                    data='deleted',
                    status=status.HTTP_200_OK
                )
        return Response(
            data="Presentation not found!",
            status=400
        )



class GetAllPresentationView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        try:
            return Response({
                    "presentations": [
                        {
                            "id": presentation.id,
                            "author": presentation.user.id,
                            "json": json.loads(presentation.json)
                        } for presentation in Presentation.objects.filter(user=request.user).all()
                    ]
                },
                status=status.HTTP_200_OK
            )
        except Exception as exc:
            return Response(
                data="Presentation not found!",
                status=400
            )

class UpdateUserInfo(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    def patch(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)  # partial=True для частичного обновления
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetUserReferralsView(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get(self, request):
        try:
            referrers = User.objects.filter(referrer=request.user).all()
            referrers_list = []

            if referrers:
                for user in referrers:
                    referrers_list.append({
                        "email" : user.email,
                        "date" : user.created_at,
                        "tokens" : 1000
                    })

            return Response(referrers_list,
                            status=status.HTTP_200_OK
                            )
        except Exception as exc:
            return Response(
                data=exc,
                status=status.HTTP_204_NO_CONTENT
            )

class ExportPresentationView(APIView):
    # authentication_classes = (JWTAuthentication, )
    # permission_classes = (IsAuthenticated, )

    def post(self, request):
        presentation_type = 'pptx'

        if request.data['pdf']:
            presentation_type = 'pdf'

        if request and request.data["id"]:
            presentation = Presentation.objects.filter(id=request.data["id"]).first()
            if presentation:
                presentation_url = export_presentation(presentation=presentation, presentation_type=presentation_type)

                return Response(
                    {
                        "id": presentation.id,
                        "pptx_url": presentation_url,
                    },
                    status=status.HTTP_200_OK
                )
        return Response(
            data="Presentation not found!",
            status=400
        )


class TariffListView(generics.ListAPIView):
    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer


class CurrentUserView(generics.RetrieveAPIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


# создание проекта

def create_project_and_get_response(user: User, project_title: str):
    try:
        new_project = PresentationsService.create_empty_project(user, project_title)
        return Response({"id": new_project.id}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class CreateNewEmptyProject(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    @atomic
    def post(self, request):
        user = request.user
        project_title = request.data.get('projectTitle', 'untitled')
        return create_project_and_get_response(user, project_title)


class CreateNewEmptyProjectForGenerating(APIView):
    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    slide_amount = 150
    reason = BalanceHistory.Reason.SLIDE_PAYMENT

    @atomic
    def post(self, request):

        if not request.data.get('projectTitle'):
            return Response({'error': "Field '' is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not request.data.get('slidesNum'):
            return Response({'error': "Field '' is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        project_title = request.data.get('projectTitle')
        slides_num = request.data.get('slidesNum')
        amount = self.slide_amount * slides_num

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
        response = create_project_and_get_response(user, project_title)

        # Если операция успешна (статус 2xx), списываем средства
        if 200 <= response.status_code < 300:
            try:
                BalanceService.decrease_balance(
                    user=request.user,
                    amount=amount,
                    reason=BalanceHistory.Reason.SLIDE_PAYMENT
                )

                updated_balance = BalanceService.get_user_balance(request.user)

                # ДОБАВЛЯЕМ ЗАГОЛОВОК ДЛЯ ФРОНТЕНДА
                if not hasattr(response, 'headers'):
                    response.headers = {}

                response.headers['X-Paid-Function'] = 'true'
                response.headers['X-Charged-Amount'] = str(amount)
                response.headers['X-Current-Balance'] = str(updated_balance.amount)
                response.headers['X-Reason'] = self.reason.value

                original_data = response.data

                extended_response = {
                    "success": True,
                    "transaction": {
                        "charged_amount": amount,
                        "previous_balance": initial_balance,
                        "new_balance": updated_balance.amount,
                        "reason": self.reason.label,
                        "transaction_message": "Средства успешно списаны"
                    },
                    "result": original_data
                }

                response.data = extended_response

            except ValidationError as e:
                print(f"Balance charge failed: {e}")

        return response


class RemoveImage(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def delete(self, request):
        filename = request.data.get('filename')

        if not filename:
            return Response({"error": "Filename is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Нормализуем путь (заменяем обратные слеши и удаляем начальный /media/ если есть)
        filename = filename.replace('\\', '/').lstrip('/')
        if filename.startswith('media/'):
            filename = filename[6:]  # Удаляем 'media/' из начала пути

        # Полный путь к файлу
        file_path = os.path.join(settings.MEDIA_ROOT, filename)

        # Проверяем, существует ли файл
        if not os.path.exists(file_path):
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем, что путь находится внутри MEDIA_ROOT (безопасность)
        file_path = os.path.normpath(file_path)
        media_root = os.path.normpath(settings.MEDIA_ROOT)
        if not file_path.startswith(media_root):
            return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            os.remove(file_path)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except OSError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UploadImage(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ImageSerializer(data=request.data)

        image = request.data.get('image')
        folder_name = request.data.get('type', 'uploaded')
        is_avatar = folder_name == 'avatar'

        if not image:
            return Response({'error':'Поле image обязательно.'}, status=status.HTTP_400_BAD_REQUEST)

        else:
            try:
                validated_image = serializer.validate_image(image)
            except serializers.ValidationError as e:
                return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)

            user_id = request.user.id  # **Получаем ID текущего пользователя**
            user_folder = os.path.join(settings.MEDIA_ROOT, folder_name, str(user_id))

            # Создание папки, если она не существует
            os.makedirs(user_folder, exist_ok=True)

            # Генерация уникального имени
            unique_filename = str(uuid.uuid4()) + '.' + validated_image.name.split(".")[-1]
            # Сохранение файла
            file_path = os.path.join(user_folder, unique_filename)

            # Проверка на существование файла с таким же содержимым. Если да - вернуть путь
            for existing_file in os.listdir(user_folder):
                existing_file_path = os.path.join(user_folder, existing_file)
                if self.files_are_identical(validated_image, existing_file_path):
                    url = os.path.join(settings.MEDIA_URL, folder_name, str(user_id), existing_file)
                    if is_avatar:
                        self.update_thumb(url)
                    return Response({'file_path': url}, status=status.HTTP_200_OK)

            with open(file_path, 'wb+') as destination:
                for chunk in image.chunks():
                    destination.write(chunk)

            # Возвращаем путь к сохранённому файлу
            url = os.path.join(settings.MEDIA_URL, folder_name, str(user_id), unique_filename)

            if is_avatar:
                self.update_thumb(url)
            return Response({'file_path': url}, status=status.HTTP_201_CREATED)

    def update_thumb(self, url):
        user = self.request.user
        user.user_thumb = url
        user.save()

    def files_are_identical(self, new_file, existing_file_path):
        """Сравнивает содержимое двух файлов."""
        with open(existing_file_path, 'rb') as f:
            existing_file_content = f.read()
            new_file_content = new_file.read()
            new_file.seek(0) # Сбросить указатель после чтения
            return existing_file_content == new_file_content

class ResetUserAvatar(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def delete(self, request):
        user = self.request.user
        user.user_thumb = None
        user.save()
        return Response(None, status=status.HTTP_200_OK)


class ListUserImages(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user_id = request.user.id
        user_folder = os.path.join(settings.MEDIA_ROOT, 'uploaded', str(user_id))

        # Создание папки пользователя, если она не существует
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        # Получение списка файлов в папке
        image_urls = []
        valid_extensions = ['jpg', 'jpeg', 'png']

        for filename in os.listdir(user_folder):
            if any(filename.lower().endswith(ext) for ext in valid_extensions):
                file_url = os.path.join(settings.MEDIA_URL, 'uploaded', str(user_id), filename)
                image_urls.append(file_url)

        return Response({'images': image_urls}, status=status.HTTP_200_OK)

class ListBackgroundImages(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        folder = os.path.join(settings.MEDIA_ROOT, 'background_images')

        # Получение списка файлов в папке
        image_urls = []
        valid_extensions = ['jpg', 'jpeg', 'png']

        for filename in os.listdir(folder):
            if any(filename.lower().endswith(ext) for ext in valid_extensions):
                file_url = os.path.join(settings.MEDIA_URL, 'background_images', filename)
                image_urls.append(file_url)

        return Response({'images': image_urls}, status=status.HTTP_200_OK)

class UpdateBalanceAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = BalanceHistorySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                if data['change_type'] == BalanceHistory.ChangeType.INCREASE:
                    BalanceService.increase_balance(
                        user=request.user,
                        amount=data['amount_change'],
                        reason=data['change_reason']
                    )
                elif data['change_type'] == BalanceHistory.ChangeType.DECREASE:
                    BalanceService.decrease_balance(
                        user=request.user,
                        amount=data['amount_change'],
                        reason=data['change_reason']
                    )

                return Response({"detail": "Balance updated successfully."}, status=status.HTTP_200_OK)

            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PromoCodeApplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=PromoCodeApplySerializer)
    @atomic
    def post(self, request):
        serializer = PromoCodeApplySerializer(data=request.data)

        if serializer.is_valid():
            promo_code = serializer.save(user=request.user)
            return Response(
                {"detail": f"Промокод '{promo_code.code}' успешно применён."},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class RoleAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RoleSerializer

    def get(self, request):
        roles = self.serializer_class(Roles.objects.all().values("id", "name"), many=True).data
        return Response(roles)