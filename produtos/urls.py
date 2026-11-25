
from django.urls import path

from .views import (
    ProdutoListView,
    ProdutoFavoritoView,
    CategoriaListView,
    ProdutoDetailView,
    CompraCreateView,
    AvaliacaoListCreateView,
    AvaliacaoDetailView,
    AdminDashboardView,
    AdminComprasView,
    CarteiraFidelidadeView,
    CupomFidelidadeListView,
    CupomFidelidadeUtilizarView,
    AdminCuponsFidelidadeView,
)


urlpatterns = [

    # =====================================================
    # PRODUTOS
    # =====================================================

    # Listar e cadastrar produtos
    path(
        "produtos/",
        ProdutoListView.as_view(),
        name="produto-list"
    ),

    # Consultar, editar e excluir produto
    path(
        "produtos/<int:id>/",
        ProdutoDetailView.as_view(),
        name="produto-detalhe"
    ),

    # Atualizar favorito
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

    # Criar compra e consultar histórico do usuário
    path(
        "compras/",
        CompraCreateView.as_view(),
        name="compra-create"
    ),

    # =====================================================
    # AVALIAÇÕES
    # =====================================================

    # Listar avaliações do usuário ou de um produto
    # Também permite cadastrar uma nova avaliação
    path(
        "avaliacoes/",
        AvaliacaoListCreateView.as_view(),
        name="avaliacao-list-create"
    ),

    # Editar uma avaliação existente
    path(
        "avaliacoes/<int:id>/",
        AvaliacaoDetailView.as_view(),
        name="avaliacao-detalhe"
    ),

    # =====================================================
    # ADMINISTRAÇÃO DAS COMPRAS
    # =====================================================

    # Listar todas as encomendas
    path(
        "compras/admin/",
        AdminComprasView.as_view(),
        name="admin-compras"
    ),

    # Consultar e atualizar uma encomenda
    path(
        "compras/admin/<int:id>/",
        AdminComprasView.as_view(),
        name="admin-compra-detalhe"
    ),

    # =====================================================
    # FIDELIDADE DO CLIENTE
    # =====================================================

    # Consultar carteira de selos do usuário autenticado
    path(
        "fidelidade/carteira/",
        CarteiraFidelidadeView.as_view(),
        name="fidelidade-carteira"
    ),

    # Listar cupons do usuário autenticado
    path(
        "fidelidade/cupons/",
        CupomFidelidadeListView.as_view(),
        name="fidelidade-cupons"
    ),

    # Validar um cupom
    path(
        "fidelidade/cupons/<str:codigo>/utilizar/",
        CupomFidelidadeUtilizarView.as_view(),
        name="fidelidade-cupom-utilizar"
    ),

    # =====================================================
    # GERENCIAMENTO DE CUPONS - ADMIN
    # =====================================================

    # Listar e pesquisar todos os cupons
    path(
        "fidelidade/admin/cupons/",
        AdminCuponsFidelidadeView.as_view(),
        name="admin-cupons-fidelidade"
    ),

    # Marcar um cupom específico como utilizado
    path(
        "fidelidade/admin/cupons/<int:id>/",
        AdminCuponsFidelidadeView.as_view(),
        name="admin-cupom-fidelidade-detalhe"
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
