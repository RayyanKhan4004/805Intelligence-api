from django.urls import path
from .views import MembershipListAPI, RegisterAPI, LoginAPI
from .views import VerifyEmailAPI

urlpatterns = [
    path('memberships/', MembershipListAPI.as_view()),  # GET all plans
    path('register/', RegisterAPI.as_view()),           # POST signup
    path('login/', LoginAPI.as_view()),                # POST login
    path('verify-email/<uuid:token>/', VerifyEmailAPI.as_view(), name='verify-email'),
]
