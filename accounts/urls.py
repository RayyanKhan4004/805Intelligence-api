from django.urls import path
from .views import MembershipListAPI, RegisterAPI, LoginAPI, VerifyEmailAPI
from .views import ForgotPasswordAPI, ResetPasswordAPI, UserProfileAPI, ChangePasswordAPI
from .views import PortfolioUserListCreateAPI, PortfolioUserDetailAPI, AcceptInviteAPI

urlpatterns = [
    path('memberships/', MembershipListAPI.as_view()),
    path('register/', RegisterAPI.as_view()),
    path('login/', LoginAPI.as_view()),
    path('verify-email/<uuid:token>/', VerifyEmailAPI.as_view(), name='verify-email'),
    path('forgot-password/', ForgotPasswordAPI.as_view(), name='forgot-password'),
    path('reset-password/<uuid:token>/', ResetPasswordAPI.as_view(), name='reset-password'),
    path('profile/', UserProfileAPI.as_view(), name='profile'),
    path('change-password/', ChangePasswordAPI.as_view(), name='change-password'),
    path('portfolio/users/', PortfolioUserListCreateAPI.as_view(), name='portfolio-users'),
    path('portfolio/users/<int:user_id>/', PortfolioUserDetailAPI.as_view(), name='portfolio-user-detail'),
    path('accept-invite/<uuid:token>/', AcceptInviteAPI.as_view(), name='accept-invite'),
]