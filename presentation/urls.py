from django.urls import path
from .views import (
    RegistrationView,
    ResendVerificationEmailView,
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

    UploadImage,
    ListUserImages,
    ListBackgroundImages,
    RemoveImage,

    GetPresentationSharedView,
    UpdateBalanceAPIView,
    PromoCodeApplyAPIView,

    GetUserReferralsView,
    UpdateUserInfo,
    ResetUserAvatar, RoleAPIView, CreateNewEmptyProjectForGenerating
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
    path('user/resend-verification/', ResendVerificationEmailView.as_view(), name='resend-verification'),
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

    path('generate/system/text', GenerateTextApiView.SystemTextGenerationAPIView.as_view()),
    path('generate/system/image', GenerateImagesAPIView.SystemImageGenerationAPIView.as_view()),

    path('generate/text', GenerateTextApiView.TextGenerationAPIView.as_view()),
    path('generate/image', GenerateImagesAPIView.ImageGenerationAPIView.as_view()),

    # Новый URL для обработки Paykeeper

    path('presentation/decrement', DecrementPresentationView.as_view()),
    # Новый URL для обработки Paykeeper
    path('paykeeper/webhook/', PaykeeperWebhookView.as_view(), name='paykeeper-webhook'),
    path('paykeeper/get_payment_link', CreatePaymentLinkView.as_view()),
    path('tariffs/', TariffListView.as_view(), name='tariff-list'),
    path('current_user/', CurrentUserView.as_view(), name='current-user'),

    path('presentation/create_empty_project', CreateNewEmptyProject.as_view()),
    path('presentation/generate_new_project', CreateNewEmptyProjectForGenerating.as_view()),

    path('file/upload', UploadImage.as_view(), name='upload_image'),
    path('file/remove', RemoveImage.as_view(), name='remove_image'),
    path('file/images_list', ListUserImages.as_view(), name='user_images'),
    path('file/background_images_list', ListBackgroundImages.as_view(), name='background_images'),

    path('users/update_balance', UpdateBalanceAPIView.as_view()),
    path('users/promocode', PromoCodeApplyAPIView.as_view()),

    path('users/roles', RoleAPIView.as_view()),

    path('user/referrals', GetUserReferralsView.as_view()),
    path('user/update', UpdateUserInfo.as_view()),
    path('user/reset_avatar', ResetUserAvatar.as_view()),
]
