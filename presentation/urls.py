from django.urls import path
from .views import (
    RegistrationView,
    VerifyEmailView,
    RequestPasswordResetView,
    ResetPasswordView,
    ChangePasswordView,
    GenerateThemesView,
    GenerateSlidesView,
    GetPresentationView,
    GetAllPresentationView,
    SavePresentationView,
    DeletePresentationView,
    ExportPresentationView,
    GetUserBalanceView,
    GenerateShortTextView,
    GenerateLongTextView,
    GenerateBulletPointsView,
    GenerateImageWithCaptionView,
    GenerateQuoteView,
    GenerateChartDataView,
    GenerateQuestionsView,
    GenerateSlideTitleView,
    GenerateSlideHeadingView,
    GenerateImagesView,
    GPTRequestView,
    PaykeeperWebhookView,  # Новый view для обработки вебхуков
    CreatePaymentLinkView,  # Новый view для получения счёта
    DecrementPresentationView,
    TariffListView,
    CurrentUserView,
    CreateNewEmptyProject,
    GetPresentationSharedView,
    UpdateBalanceAPIView,
    PromoCodeApplyAPIView,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from openai_services import (
    GenerateImagesAPIView,
    GenerateTextApiView
)

urlpatterns = [
    path('users/registration', RegistrationView.as_view()),
    path('users/verify-email', VerifyEmailView.as_view()),
    path('users/email/request-reset-password', RequestPasswordResetView.as_view()),
    path('users/email/reset-password', ResetPasswordView.as_view()),
    path('users/login', TokenObtainPairView.as_view()),
    path('users/change/password', ChangePasswordView.as_view()),
    path('users/login/refresh', TokenRefreshView.as_view()),
    path('user/presentations', GetAllPresentationView.as_view()),
    path("presentation/themes/generate", GenerateThemesView.as_view()),
    path("presentation/slides/generate", GenerateSlidesView.as_view()),
    path("presentation/get", GetPresentationView.as_view()),
    path("presentation/shared/get", GetPresentationSharedView.as_view()),
    path("presentation/save", SavePresentationView.as_view()),
    path("presentation/delete", DeletePresentationView.as_view()),
    path("presentation/export", ExportPresentationView.as_view()),
    path("presentation/getbalance", GetUserBalanceView.as_view()),  

    # Новые URL
    path("presentation/short_text/generate", GenerateShortTextView.as_view()),
    path("presentation/long_text/generate", GenerateLongTextView.as_view()),
    path("presentation/bullet_points/generate", GenerateBulletPointsView.as_view()),
    path("presentation/image_with_caption/generate", GenerateImageWithCaptionView.as_view()),
    path("presentation/quote/generate", GenerateQuoteView.as_view()),
    path("presentation/chart_data/generate", GenerateChartDataView.as_view()),
    path("presentation/questions/generate", GenerateQuestionsView.as_view()),
    path("presentation/slide_title/generate", GenerateSlideTitleView.as_view()),
    path("presentation/slide_heading/generate", GenerateSlideHeadingView.as_view()),
    path("presentation/images/generate", GenerateImagesView.as_view()),
    path('presentation/gpt/request', GPTRequestView.as_view()),

    path('generate/text', GenerateTextApiView.TextGenerationAPIView.as_view()),
    path('generate/image', GenerateImagesAPIView.ImageGenerationAPIView.as_view()),

    # Новый URL для обработки Paykeeper 

    path('presentation/decrement', DecrementPresentationView.as_view()),
    # Новый URL для обработки Paykeeper
    path('paykeeper/webhook/', PaykeeperWebhookView.as_view(), name='paykeeper-webhook'),
    path('paykeeper/get_payment_link', CreatePaymentLinkView.as_view()),
    path('tariffs/', TariffListView.as_view(), name='tariff-list'),
    path('current_user/', CurrentUserView.as_view(), name='current-user'),
    path('presentation/new', CreateNewEmptyProject.as_view()),
    path('users/update_balance', UpdateBalanceAPIView.as_view()),
    path('users/promocode', PromoCodeApplyAPIView.as_view()),
]
