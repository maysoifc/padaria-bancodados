from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    # Administração do Django
    path("admin/", admin.site.urls),

    # API de produtos, categorias, compras e dashboard
    path("api/", include("produtos.urls")),

    # API de usuários, cadastro, login e perfis
    path("api/", include("perfis.urls")),
]