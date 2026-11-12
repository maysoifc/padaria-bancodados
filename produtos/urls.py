
from django.urls import path

from .views import (
    ProdutoListView,
    ProdutoFavoritoView,
    CategoriaListView,
    ProdutoDetailView,
    CompraCreateView,
    AdminDashboardView,
    AdminComprasView,
)


urlpatterns = [
    # =====================================================
    # PRODUTOS
    # =====================================================

    path(
        "produtos/",
        ProdutoListView.as_view(),
        name="produto-list"
    ),

    path(
        "produtos/<int:id>/",
        ProdutoDetailView.as_view(),
        name="produto-detalhe"
    ),

    path(
        "produtos/<int:id>/favorito/",
        ProdutoFavoritoView.as_view(),
        name="produto-favorito"
    ),

    # =====================================================
    # CATEGORIAS
    # =====================================================

    path(
        "categorias/",
        CategoriaListView.as_view(),
        name="categoria-list"
    ),

    # =====================================================
    # COMPRAS
    # =====================================================

    path(
        "compras/",
        CompraCreateView.as_view(),
        name="compra-create"
    ),

    # =====================================================
    # ADMINISTRAÇÃO DAS COMPRAS
    # =====================================================

    path(
        "compras/admin/",
        AdminComprasView.as_view(),
        name="admin-compras"
    ),

    path(
        "compras/admin/<int:id>/",
        AdminComprasView.as_view(),
        name="admin-compra-detalhe"
    ),

    # =====================================================
    # DASHBOARD ADMINISTRATIVO
    # =====================================================

    path(
        "admin/dashboard/",
        AdminDashboardView.as_view(),
        name="admin-dashboard"
    ),
]