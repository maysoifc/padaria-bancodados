from django.urls import path
from .views import CadastroView, LoginView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('cadastro/', CadastroView.as_view(), name='cadastro'),
    path('login/', LoginView.as_view(), name='login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]