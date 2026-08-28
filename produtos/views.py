from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Produto, Categoria
from .serializers import ProdutoSerializer
from django.shortcuts import get_object_or_404

class ProdutoListView(APIView):
    def get(self, request):
        categoria_nome = request.query_params.get('categoria')
        
        # --- DEBUG TOTAL ---
        print(f"DEBUG: O que o Frontend enviou: '{categoria_nome}'")
        
        # Vamos ver todos os produtos e suas categorias reais no banco
        produtos_no_banco = Produto.objects.all()
        for p in produtos_no_banco:
            cats = list(p.categorias.values_list('nome_categoria', flat=True))
            print(f"DEBUG: Produto '{p.nome}' tem as categorias: {cats}")
        # -------------------
        
        produtos = Produto.objects.all()
        
        if categoria_nome and categoria_nome != '':
            produtos = produtos.filter(
                categorias__nome_categoria__icontains=categoria_nome.strip()
            ).distinct()
            
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