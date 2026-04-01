from django.urls import path
from .views import MembershipListAPI, RegisterAPI, LoginAPI, VerifyEmailAPI
from .views import ForgotPasswordAPI, ResetPasswordAPI

urlpatterns = [
    path('memberships/', MembershipListAPI.as_view()),
    path('register/', RegisterAPI.as_view()),
    path('login/', LoginAPI.as_view()),
    path('verify-email/<uuid:token>/', VerifyEmailAPI.as_view(), name='verify-email'),
    path('forgot-password/', ForgotPasswordAPI.as_view(), name='forgot-password'),
    path('reset-password/<uuid:token>/', ResetPasswordAPI.as_view(), name='reset-password'),
]