from django.urls import path
from .views import ProdutoListView, ProdutoFavoritoView

urlpatterns = [
    path('produtos/', ProdutoListView.as_view(), name='produto-list'),
    path('produtos/<int:id>/favorito/', ProdutoFavoritoView.as_view(), name='produto-favorito'),
]