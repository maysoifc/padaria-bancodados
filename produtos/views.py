
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import (
    Count,
    Sum,
    F,
    DecimalField,
    ExpressionWrapper,
)
from django.db.models.functions import TruncMonth
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Produto, Categoria, Compra, ItemCompra
from .serializers import ProdutoSerializer, CompraSerializer


# =========================================================
# VERIFICAÇÃO DE ADMINISTRADOR
# =========================================================

def usuario_e_admin(request):
    usuario = request.user

    return (
        usuario.is_authenticated
        and (
            usuario.is_staff
            or usuario.is_superuser
        )
    )


def resposta_sem_permissao(mensagem):
    return Response(
        {"erro": mensagem},
        status=status.HTTP_403_FORBIDDEN
    )


def resposta_nao_autenticado():
    return Response(
        {"erro": "É necessário estar autenticado."},
        status=status.HTTP_401_UNAUTHORIZED
    )


# =========================================================
# CÁLCULO DO PREÇO COM DESCONTO
# =========================================================

def calcular_preco_com_desconto(produto):
    """
    Calcula o preço final usando o preço e o percentual
    de desconto cadastrados no banco de dados.
    """

    preco = Decimal(str(produto.preco or "0.00"))
    desconto = Decimal(str(produto.desconto or "0.00"))

    if desconto < 0 or desconto > 100:
        raise ValueError("O desconto deve estar entre 0% e 100%.")

    preco_final = preco * (
        Decimal("1.00") - desconto / Decimal("100.00")
    )

    return preco_final.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# =========================================================
# PRODUTOS
# =========================================================

class ProdutoListView(APIView):

    def get(self, request):

        categoria_nome = request.query_params.get("categoria")

        produtos = (
            Produto.objects
            .prefetch_related("categorias")
            .all()
            .order_by("nome")
        )

        if categoria_nome:
            produtos = produtos.filter(
                categorias__nome_categoria__icontains=categoria_nome.strip()
            ).distinct()

        serializer = ProdutoSerializer(
            produtos,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request):

        if not request.user.is_authenticated:
            return resposta_nao_autenticado()

        if not usuario_e_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para cadastrar produtos."
            )

        serializer = ProdutoSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                {
                    "erro": "Não foi possível cadastrar o produto.",
                    "detalhes": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            produto = serializer.save()

        return Response(
            {
                "mensagem": "Produto cadastrado com sucesso!",
                "produto": ProdutoSerializer(produto).data
            },
            status=status.HTTP_201_CREATED
        )


class ProdutoDetailView(APIView):

    def get_produto(self, id):
        return get_object_or_404(
            Produto.objects.prefetch_related("categorias"),
            idProduto=id
        )

    # -----------------------------------------------------
    # CONSULTAR PRODUTO
    # -----------------------------------------------------

    def get(self, request, id):

        produto = self.get_produto(id)

        serializer = ProdutoSerializer(produto)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    # -----------------------------------------------------
    # ATUALIZAR PRODUTO COMPLETAMENTE
    # -----------------------------------------------------

    def put(self, request, id):

        return self.atualizar_produto(
            request,
            id,
            parcial=False
        )

    # -----------------------------------------------------
    # ATUALIZAR PRODUTO PARCIALMENTE
    # -----------------------------------------------------

    def patch(self, request, id):

        return self.atualizar_produto(
            request,
            id,
            parcial=True
        )

    # -----------------------------------------------------
    # MÉTODO COMPARTILHADO DE ATUALIZAÇÃO
    # -----------------------------------------------------

    def atualizar_produto(self, request, id, parcial=False):

        if not request.user.is_authenticated:
            return resposta_nao_autenticado()

        if not usuario_e_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para editar produtos."
            )

        produto = self.get_produto(id)

        serializer = ProdutoSerializer(
            produto,
            data=request.data,
            partial=parcial
        )

        if not serializer.is_valid():
            return Response(
                {
                    "erro": "Não foi possível atualizar o produto.",
                    "detalhes": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            produto = serializer.save()

        return Response(
            {
                "mensagem": "Produto atualizado com sucesso!",
                "produto": ProdutoSerializer(produto).data
            },
            status=status.HTTP_200_OK
        )

    # -----------------------------------------------------
    # EXCLUIR PRODUTO
    # -----------------------------------------------------

    def delete(self, request, id):

        if not request.user.is_authenticated:
            return resposta_nao_autenticado()

        if not usuario_e_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para excluir produtos."
            )

        produto = self.get_produto(id)

        try:
            with transaction.atomic():
                produto.delete()

        except ProtectedError:
            return Response(
                {
                    "erro": (
                        "Este produto está vinculado a compras anteriores "
                        "e não pode ser excluído para preservar o histórico."
                    )
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            {
                "mensagem": "Produto excluído com sucesso!"
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# FAVORITOS
# =========================================================

class ProdutoFavoritoView(APIView):

    def patch(self, request, id):

        produto = get_object_or_404(
            Produto,
            idProduto=id
        )

        favorito = request.data.get(
            "favorito",
            produto.favorito
        )

        if not isinstance(favorito, bool):
            return Response(
                {
                    "erro": "O campo favorito deve ser verdadeiro ou falso."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        produto.favorito = favorito

        produto.save(
            update_fields=["favorito"]
        )

        return Response(
            {
                "mensagem": "Favorito atualizado com sucesso.",
                "favorito": produto.favorito
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# CATEGORIAS
# =========================================================

class CategoriaListView(APIView):

    def get(self, request):

        categorias = Categoria.objects.all().order_by(
            "nome_categoria"
        )

        resultado = [
            {
                "idCategoria": categoria.idCategoria,
                "nome_categoria": categoria.nome_categoria
            }
            for categoria in categorias
        ]

        return Response(
            resultado,
            status=status.HTTP_200_OK
        )


# =========================================================
# COMPRAS
# =========================================================

class CompraCreateView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        nome = str(
            request.data.get("nome", "")
        ).strip()

        telefone = str(
            request.data.get("telefone", "")
        ).strip()

        forma_pagamento = str(
            request.data.get("formaPagamento", "")
        ).strip().lower()

        itens = request.data.get("itens", [])

        # -------------------------------------------------
        # VALIDAR DADOS PRINCIPAIS
        # -------------------------------------------------

        if not nome:
            return Response(
                {"erro": "Nome é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not telefone:
            return Response(
                {"erro": "Telefone é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if forma_pagamento not in ["pix", "cartao"]:
            return Response(
                {"erro": "Forma de pagamento inválida."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(itens, list) or not itens:
            return Response(
                {
                    "erro": "A compra precisa ter pelo menos um produto."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        itens_validados = []

        # -------------------------------------------------
        # VALIDAR CADA PRODUTO
        # -------------------------------------------------

        for item in itens:

            if not isinstance(item, dict):
                return Response(
                    {
                        "erro": "Os dados dos produtos são inválidos."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            produto_id_recebido = item.get("idProduto")

            quantidade_recebida = item.get(
                "quantidade",
                item.get("qtd", 1)
            )

            try:
                if isinstance(produto_id_recebido, bool):
                    raise ValueError

                produto_id = int(produto_id_recebido)

                if str(produto_id_recebido).strip() != str(produto_id):
                    raise ValueError

                if isinstance(quantidade_recebida, bool):
                    raise ValueError

                quantidade = int(quantidade_recebida)

                if str(quantidade_recebida).strip() != str(quantidade):
                    raise ValueError

            except (TypeError, ValueError):
                return Response(
                    {
                        "erro": "Produto ou quantidade inválidos."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if produto_id < 1 or quantidade < 1:
                return Response(
                    {
                        "erro": "O produto e a quantidade devem ser válidos."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            produto = Produto.objects.filter(
                idProduto=produto_id
            ).first()

            if produto is None:
                return Response(
                    {
                        "erro": f"Produto com ID {produto_id} não encontrado."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            itens_validados.append(
                (produto, quantidade)
            )

        # -------------------------------------------------
        # CRIAR COMPRA
        # -------------------------------------------------

        compra = Compra.objects.create(
            usuario=request.user,
            nome=nome,
            telefone=telefone,
            forma_pagamento=forma_pagamento
        )

        # -------------------------------------------------
        # CRIAR ITENS COM DESCONTO APLICADO
        # -------------------------------------------------

        itens_compra = []

        for produto, quantidade in itens_validados:

            preco_final = calcular_preco_com_desconto(
                produto
            )

            itens_compra.append(
                ItemCompra(
                    compra=compra,
                    produto=produto,
                    quantidade=quantidade,
                    preco_unitario=preco_final
                )
            )

        ItemCompra.objects.bulk_create(
            itens_compra
        )

        # -------------------------------------------------
        # RECUPERAR COMPRA COMPLETA
        # -------------------------------------------------

        compra = (
            Compra.objects
            .prefetch_related(
                "itens__produto__categorias"
            )
            .get(
                idCompra=compra.idCompra
            )
        )

        serializer = CompraSerializer(compra)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


# =========================================================
# DASHBOARD ADMINISTRATIVO
# =========================================================

class AdminDashboardView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        if not usuario_e_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para acessar o painel."
            )

        Usuario = get_user_model()

        hoje = timezone.localdate()

        meses = []

        # -------------------------------------------------
        # ÚLTIMOS SEIS MESES, INCLUINDO O ATUAL
        # -------------------------------------------------

        for deslocamento in reversed(range(6)):

            indice = (
                hoje.year * 12
                + hoje.month - 1
                - deslocamento
            )

            ano = indice // 12
            mes = indice % 12 + 1

            meses.append(
                date(ano, mes, 1)
            )

        inicio_periodo = datetime.combine(
            meses[0],
            time.min
        )

        if settings.USE_TZ:
            inicio_periodo = timezone.make_aware(
                inicio_periodo
            )

        compras_periodo = Compra.objects.filter(
            criado_em__gte=inicio_periodo
        )

        # -------------------------------------------------
        # QUANTIDADE DE ENCOMENDAS POR MÊS
        # -------------------------------------------------

        compras_por_mes = (
            compras_periodo
            .annotate(
                mes=TruncMonth("criado_em")
            )
            .values("mes")
            .annotate(
                total=Count("idCompra")
            )
            .order_by("mes")
        )

        # -------------------------------------------------
        # FATURAMENTO POR MÊS
        # -------------------------------------------------

        valor_item = ExpressionWrapper(
            F("quantidade") * F("preco_unitario"),
            output_field=DecimalField(
                max_digits=12,
                decimal_places=2
            )
        )

        valores_por_mes = (
            ItemCompra.objects
            .filter(
                compra__criado_em__gte=inicio_periodo
            )
            .exclude(
                compra__status="cancelado"
            )
            .annotate(
                mes=TruncMonth("compra__criado_em")
            )
            .values("mes")
            .annotate(
                total=Sum(valor_item)
            )
            .order_by("mes")
        )

        quantidade_meses = {
            item["mes"].strftime("%Y-%m"): item["total"]
            for item in compras_por_mes
            if item["mes"]
        }

        valores_meses = {
            item["mes"].strftime("%Y-%m"): (
                item["total"] or Decimal("0.00")
            )
            for item in valores_por_mes
            if item["mes"]
        }

        nomes_meses = [
            "Jan", "Fev", "Mar", "Abr",
            "Mai", "Jun", "Jul", "Ago",
            "Set", "Out", "Nov", "Dez"
        ]

        grafico = []

        for mes in meses:

            chave = mes.strftime("%Y-%m")

            grafico.append({
                "mes": nomes_meses[mes.month - 1],
                "encomendas": quantidade_meses.get(
                    chave,
                    0
                ),
                "faturamento": float(
                    valores_meses.get(
                        chave,
                        Decimal("0.00")
                    )
                )
            })

        # -------------------------------------------------
        # CINCO ÚLTIMAS ENCOMENDAS
        # -------------------------------------------------

        total_compra = ExpressionWrapper(
            F("itens__quantidade") * F("itens__preco_unitario"),
            output_field=DecimalField(
                max_digits=12,
                decimal_places=2
            )
        )

        ultimas = (
            Compra.objects
            .annotate(
                total=Sum(total_compra)
            )
            .order_by("-criado_em")[:5]
        )

        ultimas_encomendas = []

        for compra in ultimas:

            ultimas_encomendas.append({
                "id": compra.idCompra,
                "cliente": compra.nome,
                "data": compra.criado_em.isoformat(),
                "pagamento": compra.forma_pagamento,
                "status": compra.status,
                "total": float(
                    compra.total or Decimal("0.00")
                )
            })

        # -------------------------------------------------
        # RESPOSTA DO DASHBOARD
        # -------------------------------------------------

        return Response(
            {
                "resumo": {
                    "produtos": Produto.objects.count(),
                    "categorias": Categoria.objects.count(),
                    "encomendas": Compra.objects.count(),
                    "usuarios": Usuario.objects.count()
                },
                "grafico": grafico,
                "ultimas_encomendas": ultimas_encomendas
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# GERENCIAMENTO DE ENCOMENDAS - ADMIN
# =========================================================

class AdminComprasView(APIView):

    permission_classes = [IsAuthenticated]

    def verificar_admin(self, request):
        return usuario_e_admin(request)

    # -----------------------------------------------------
    # SERIALIZAR COMPRA PARA O PAINEL
    # -----------------------------------------------------

    def serializar_compra(self, compra):

        itens = []

        total = Decimal("0.00")

        for item in compra.itens.all():

            subtotal = (
                item.preco_unitario * item.quantidade
            )

            total += subtotal

            itens.append({
                "id": item.idItemCompra,
                "idProduto": item.produto.idProduto,
                "nome": item.produto.nome,
                "quantidade": item.quantidade,

                # Preço efetivamente cobrado na compra.
                "preco": float(item.preco_unitario),
                "preco_unitario": float(item.preco_unitario),

                "subtotal": float(subtotal)
            })

        return {
            "id": compra.idCompra,
            "idCompra": compra.idCompra,
            "nome": compra.nome,
            "telefone": compra.telefone,
            "email": compra.usuario.email,
            "forma_pagamento": compra.forma_pagamento,
            "status": compra.status,
            "criado_em": compra.criado_em.isoformat(),
            "total": float(total),
            "itens": itens
        }

    # -----------------------------------------------------
    # LISTAR TODAS AS ENCOMENDAS
    # -----------------------------------------------------

    def get(self, request):

        if not self.verificar_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para acessar as compras."
            )

        compras = (
            Compra.objects
            .select_related("usuario")
            .prefetch_related("itens__produto")
            .order_by("-criado_em")
        )

        resultado = [
            self.serializar_compra(compra)
            for compra in compras
        ]

        return Response(
            resultado,
            status=status.HTTP_200_OK
        )

    # -----------------------------------------------------
    # ATUALIZAR STATUS DE UMA ENCOMENDA
    # -----------------------------------------------------

    def patch(self, request, id):

        if not self.verificar_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para alterar as compras."
            )

        compra = get_object_or_404(
            Compra.objects
            .select_related("usuario")
            .prefetch_related("itens__produto"),
            idCompra=id
        )

        novo_status = request.data.get("status")

        status_validos = dict(
            Compra.STATUS_CHOICES
        )

        if novo_status not in status_validos:
            return Response(
                {
                    "erro": "Status inválido.",
                    "status_disponiveis": list(
                        status_validos.keys()
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        compra.status = novo_status

        compra.save(
            update_fields=["status"]
        )

        return Response(
            {
                "mensagem": "Status da encomenda atualizado com sucesso.",
                "compra": self.serializar_compra(compra)
            },
            status=status.HTTP_200_OK
        )
