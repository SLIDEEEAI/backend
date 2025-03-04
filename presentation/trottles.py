from rest_framework.throttling import AnonRateThrottle


class EnterPasswordReset(AnonRateThrottle):
    scope = 'enter-request-reset-password'


class RequestToResetPassword(AnonRateThrottle):
    scope = 'request-reset-password'
