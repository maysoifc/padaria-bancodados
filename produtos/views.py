from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Produto
from .serializers import ProdutoSerializer

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
            return Response({"mensagem": "Atualizado com sucesso"})
        except Produto.DoesNotExist:
            return Response({"erro": "Produto não encontrado"}, status=status.HTTP_404_NOT_FOUND)