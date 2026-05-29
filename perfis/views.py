from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UsuarioSerializer

class CadastroView(generics.CreateAPIView):
    serializer_class = UsuarioSerializer

class LoginView(TokenObtainPairView):
    pass

class PerfilView(APIView):
    permission_classes = [IsAuthenticated] # Isso causa o 403 se o token for inválido/ausente

    def get(self, request):
        return Response({
            "username": request.user.username,
            "email": request.user.email
        })