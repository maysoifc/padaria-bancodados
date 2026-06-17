from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Produto
from .serializers import ProdutoSerializer
from .models import Categoria
from django.shortcuts import get_object_or_404

class ProdutoListView(APIView):
    def get(self, request):
        categoria_nome = request.query_params.get('categoria')
        if categoria_nome and categoria_nome != 'Todos os produtos':
            produtos = Produto.objects.filter(categorias__nome_categoria=categoria_nome).distinct()
        else:
            produtos = Produto.objects.all()
        serializer = ProdutoSerializer(produtos, many=True)
        return Response(serializer.data)

class ProdutoFavoritoView(APIView):
    def patch(self, request, id):
        try:
            produto = Produto.objects.get(idProduto=id)
            produto.favorito = request.data.get('favorito', produto.favorito)
            produto.save()
            return Response({"mensagem": "Atualizado"})
        except Produto.DoesNotExist:
            return Response({"erro": "Não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        
class CategoriaListView(APIView):
    def get(self, request):
        categorias = Categoria.objects.all().values('idCategoria', 'nome_categoria')
        return Response(list(categorias))
    
class ProdutoDetailView(APIView):
    def get(self, request, id):
        produto = get_object_or_404(Produto, idProduto=id)
        serializer = ProdutoSerializer(produto)
        return Response(serializer.data)