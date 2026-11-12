from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Usuario

from .serializers import (
    UsuarioSerializer,
    AdminUsuarioSerializer,
    AdminTokenObtainPairSerializer,
)


class CadastroView(generics.CreateAPIView):
    serializer_class = UsuarioSerializer


class LoginView(TokenObtainPairView):
    pass


class AdminLoginView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UsuarioSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class AdminUsuariosView(generics.ListAPIView):
    serializer_class = AdminUsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user

        if not (usuario.is_staff or usuario.is_superuser):
            raise PermissionDenied(
                "Você não tem permissão para consultar os usuários."
            )

        return Usuario.objects.all().order_by("-date_joined")
