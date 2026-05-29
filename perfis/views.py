from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UsuarioSerializer

class CadastroView(generics.CreateAPIView):
    serializer_class = UsuarioSerializer

class LoginView(TokenObtainPairView):
    # O JWT já lida com a autenticação e retorna access/refresh tokens
    pass