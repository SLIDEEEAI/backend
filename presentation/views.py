from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login
import openai  # Добавляем импорт openai_services

import json
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import AccessToken
from presentation.models import User, Presentation

from .serializers import (
    RegistrationSerializer,
    ChangePasswordSerializer,
    GenerateThemesSerializer,
    GenerateSlidesSerializer,
    GPTRequestSerializer,
    GetPresentationSerializer,
)

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
    generate_images,
    generate_images2,
    generate_custom_request,
)

import requests
import base64
import json

# новые
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from .models import User  # Импортируйте вашу модель User

from .serializers import PaykeeperWebhookSerializer



class PaykeeperWebhookView(APIView):
    # authentication_classes = (JWTAuthentication, )
    # permission_classes = (IsAuthenticated, )

    def post(self, request):
        try:

            user = User.objects.filter(id=request.data.get('clientid')).first()

            if user:
                # user.balance += round( int (request.data.get('sum') ) )
                user.balance += 100
                user.save()
                return JsonResponse({'status': 'success'}, status=200)
            else:
                return JsonResponse({'status': 'user not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'invalid data'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class CreatePaymentLinkView(APIView):

    authentication_classes = (JWTAuthentication, )
    permission_classes = (IsAuthenticated, )

    # Логин и пароль от личного кабинета PayKeeper
    user = "admin"
    password = "67f53b702716"

    def post(self, request):
        try:

            # Basic-авторизация передаётся как base64
            credentials = f"{self.user}:{self.password}"
            base64_credentials = base64.b64encode(credentials.encode()).decode('utf-8')
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {base64_credentials}'
            }

            # Укажите адрес ВАШЕГО сервера PayKeeper, адрес demo.paykeeper.ru - пример!
            server_paykeeper = "https://slideeeeeee.server.paykeeper.ru"

            # Параметры платежа, сумма - обязательный параметр
            # Остальные параметры можно не задавать
            payment_data = {
                "pay_amount": request.data.get('pay_amount'),
                "clientid": request.data.get('clientid'),
                "orderid": request.data.get('orderid'),
                "client_email": request.data.get('client_email'),
                "service_name": request.data.get('service_name'),
                "client_phone": request.data.get('client_phone')
            }

            # Готовим первый запрос на получение токена безопасности
            uri = "/info/settings/token/"
            response = requests.get(server_paykeeper + uri, headers=headers)
            php_array = response.json()

            # В ответе должно быть заполнено поле token, иначе - ошибка
            token = php_array.get('token')
            if not token:
                raise ValueError('Token not found')

            # Готовим запрос 3.4 JSON API на получение счёта
            uri = "/change/invoice/preview/"
            payload = {**payment_data, 'token': token}
            response = requests.post(server_paykeeper + uri, headers=headers, data=payload)
            response_data = response.json()

            # В ответе должно быть поле invoice_id, иначе - ошибка
            invoice_id = response_data.get('invoice_id')
            if not invoice_id:
                raise ValueError('Invoice ID not found')

            # В этой переменной прямая ссылка на оплату с заданными параметрами
            link = f"{server_paykeeper}/bill/{invoice_id}/"

            # Теперь её можно использовать как угодно, например, выводим ссылку на оплату
            return JsonResponse( { 'link': link } , status=200 )

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
                        "balance" : user.balance
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
        image_url, caption = generate_image_with_caption(presentation_theme)
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
        
        image_urls = generate_images(presentation_theme, num_images)
        
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
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Создать пользователя и установить баланс
        initial_balance = request.data.get('balance', 1000)  # По умолчанию 1000
        User.objects.create(email=request.data['email'], balance=initial_balance)

        response_data = {
            'user_id': user.id,  # Возвращаем идентификатор пользователя вместе с ответом
            'access': str(serializer.validated_data['access']),
            'refresh': str(serializer.validated_data['refresh']),
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

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
        if user.balance < 10:
            return Response(
                {"error": "Insufficient funds"},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )

        # Списываем средства
        user.balance -= 10
        user.save()

        # Создаем презентацию
        presentation = Presentation.objects.create(
            user=user,
            json=generate_json_object(
                request.data["themes"],
                serializer.data["slides"],
                generate_images_from_list(serializer.data["slides"])
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
                        "balance" : presentation.user.balance
                    },
                    status=status.HTTP_201_CREATED
                )
        return Response(
            data="Presentation not found!",
            status=400
        )

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