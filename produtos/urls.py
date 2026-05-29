from django.urls import path
from .views import ProdutoListView, ProdutoFavoritoView, CategoriaListView 

urlpatterns = [
    path('produtos/', ProdutoListView.as_view(), name='produto-list'),
    path('produtos/<int:id>/favorito/', ProdutoFavoritoView.as_view(), name='produto-favorito'),
    path('categorias/', CategoriaListView.as_view(), name='categoria-list'),
]