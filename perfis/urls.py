from django.urls import path

from .views import (
    CadastroView,
    LoginView,
    PerfilView,
    AdminLoginView,
    AdminUsuariosView,
)

urlpatterns = [
    path("cadastro/", CadastroView.as_view(), name="cadastro"),
    path("login/", LoginView.as_view(), name="login"),
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("perfil/", PerfilView.as_view(), name="perfil"),
    path("usuarios/", AdminUsuariosView.as_view(), name="admin-usuarios"),
]
