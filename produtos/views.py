
import random
import secrets

from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
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

from .models import (
    Produto,
    Categoria,
    Avaliacao,
    Compra,
    ItemCompra,
    CarteiraFidelidade,
    CupomFidelidade,
)

from .serializers import (
    ProdutoSerializer,
    AvaliacaoSerializer,
    CompraSerializer,
)


# =========================================================
# CONFIGURAÇÕES DA FIDELIDADE
# =========================================================

TOTAL_SELOS_FIDELIDADE = 10
VALOR_MINIMO_FIDELIDADE = Decimal("20.00")

PREMIOS_FIDELIDADE = [
    {
        "tipo": "produto",
        "titulo": "Torta grátis",
        "descricao": "Ganhe uma torta por nossa conta.",
        "icone": "fa-solid fa-cake-candles",
    },
    {
        "tipo": "desconto",
        "titulo": "10% de desconto",
        "descricao": "Ganhe 10% de desconto em sua compra.",
        "icone": "fa-solid fa-tag",
    },
    {
        "tipo": "desconto",
        "titulo": "25% de desconto",
        "descricao": "Ganhe 25% de desconto em sua compra.",
        "icone": "fa-solid fa-tags",
    },
    {
        "tipo": "desconto",
        "titulo": "50% de desconto",
        "descricao": "Ganhe 50% de desconto em sua compra.",
        "icone": "fa-solid fa-gift",
    },
    {
        "tipo": "produto",
        "titulo": "Pão grátis",
        "descricao": "Ganhe um pão por nossa conta.",
        "icone": "fa-solid fa-bread-slice",
    },
    {
        "tipo": "produto",
        "titulo": "Café grátis",
        "descricao": "Ganhe um café por nossa conta.",
        "icone": "fa-solid fa-mug-hot",
    },
    {
        "tipo": "produto",
        "titulo": "Doce grátis",
        "descricao": "Ganhe um doce por nossa conta.",
        "icone": "fa-solid fa-cookie-bite",
    },
]


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
        raise ValueError(
            "O desconto deve estar entre 0% e 100%."
        )

    preco_final = preco * (
        Decimal("1.00") - desconto / Decimal("100.00")
    )

    return preco_final.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# =========================================================
# VALIDAÇÃO DE COMPRA PARA AVALIAÇÃO
# =========================================================

def usuario_comprou_produto(usuario, produto):
    """
    Só permite criar avaliações para produtos que aparecem
    em compras do próprio usuário com pagamento confirmado
    e que não estejam canceladas.
    """

    return ItemCompra.objects.filter(
        compra__usuario=usuario,
        compra__pagamento_confirmado=True,
        produto=produto,
    ).exclude(
        compra__status="cancelado"
    ).exists()


# =========================================================
# FUNÇÕES AUXILIARES DA FIDELIDADE
# =========================================================

def calcular_total_compra(compra):
    total = Decimal("0.00")

    for item in compra.itens.all():
        total += (
            Decimal(str(item.preco_unitario))
            * Decimal(str(item.quantidade))
        )

    return total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def criar_cupom_fidelidade(usuario):
    premio = random.choice(PREMIOS_FIDELIDADE)

    while True:
        codigo = f"MARTINS-{secrets.token_hex(3).upper()}"

        if not CupomFidelidade.objects.filter(
            codigo=codigo
        ).exists():
            break

    return CupomFidelidade.objects.create(
        usuario=usuario,
        codigo=codigo,
        titulo=premio["titulo"],
        descricao=premio["descricao"],
        tipo=premio["tipo"],
        icone=premio["icone"],
        status="disponivel",
    )


def creditar_selo_da_compra(compra):
    """
    Credita no máximo um selo por compra.

    Deve ser chamada dentro de uma transação e depois
    da confirmação do pagamento.
    """

    if compra.selo_creditado:
        return {
            "creditado": False,
            "mensagem": "Esta compra já foi processada pela fidelidade.",
            "cupom": None,
        }

    total = calcular_total_compra(compra)

    if total < VALOR_MINIMO_FIDELIDADE:
        compra.selo_creditado = True
        compra.save(
            update_fields=["selo_creditado"]
        )

        return {
            "creditado": False,
            "mensagem": "O valor mínimo para ganhar um selo é R$ 20,00.",
            "cupom": None,
        }

    Usuario = get_user_model()

    usuario = Usuario.objects.select_for_update().get(
        pk=compra.usuario_id
    )

    carteira, _ = CarteiraFidelidade.objects.get_or_create(
        usuario=usuario
    )

    carteira = (
        CarteiraFidelidade.objects
        .select_for_update()
        .get(pk=carteira.pk)
    )

    carteira.selos += 1

    cupom = None

    if carteira.selos >= TOTAL_SELOS_FIDELIDADE:
        cupom = criar_cupom_fidelidade(usuario)
        carteira.selos = 0

    carteira.save(
        update_fields=[
            "selos",
            "atualizado_em"
        ]
    )

    compra.selo_creditado = True

    compra.save(
        update_fields=["selo_creditado"]
    )

    return {
        "creditado": True,
        "mensagem": (
            "Parabéns! Você ganhou um selo."
            if cupom is None
            else "Parabéns! Você completou seu cartão e ganhou um cupom."
        ),
        "cupom": cupom,
    }


def serializar_cupom_fidelidade(cupom):
    return {
        "id": cupom.pk,
        "codigo": cupom.codigo,
        "titulo": cupom.titulo,
        "descricao": cupom.descricao,
        "tipo": cupom.tipo,
        "icone": cupom.icone,
        "status": cupom.status,
        "criado_em": (
            cupom.criado_em.isoformat()
            if cupom.criado_em else None
        ),
        "utilizado_em": (
            cupom.utilizado_em.isoformat()
            if cupom.utilizado_em else None
        ),
        "compra_id": (
            cupom.compra_id
            if cupom.compra_id else None
        ),
    }


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

    def get(self, request, id):

        produto = self.get_produto(id)

        serializer = ProdutoSerializer(produto)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def put(self, request, id):

        return self.atualizar_produto(
            request,
            id,
            parcial=False
        )

    def patch(self, request, id):

        return self.atualizar_produto(
            request,
            id,
            parcial=True
        )

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

    def get(self, request):

        compras = (
            Compra.objects
            .filter(usuario=request.user)
            .prefetch_related(
                "itens__produto__categorias"
            )
            .order_by("-criado_em")
        )

        serializer = CompraSerializer(
            compras,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

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

        compra = Compra.objects.create(
            usuario=request.user,
            nome=nome,
            telefone=telefone,
            forma_pagamento=forma_pagamento
        )

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
# AVALIAÇÕES
# =========================================================

class AvaliacaoListCreateView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Sem ?produto: retorna as avaliações do usuário autenticado.
        Com ?produto=id: retorna as avaliações públicas do produto.
        """

        avaliacoes = (
            Avaliacao.objects
            .select_related("usuario", "produto")
            .order_by("-criado_em")
        )

        produto_id = request.query_params.get("produto")

        if produto_id:
            try:
                produto_id = int(produto_id)

                if produto_id < 1:
                    raise ValueError

            except (TypeError, ValueError):
                return Response(
                    {"erro": "ID de produto inválido."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            avaliacoes = avaliacoes.filter(
                produto__idProduto=produto_id
            )

        else:
            avaliacoes = avaliacoes.filter(
                usuario=request.user
            )

        serializer = AvaliacaoSerializer(
            avaliacoes,
            many=True,
            context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request):

        serializer = AvaliacaoSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():
            return Response(
                {
                    "erro": "Não foi possível registrar a avaliação.",
                    "detalhes": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        produto = serializer.validated_data["produto"]

        if not usuario_comprou_produto(
            request.user,
            produto
        ):
            return Response(
                {
                    "erro": (
                        "Você só pode avaliar produtos de compras "
                        "com pagamento confirmado e não canceladas."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            with transaction.atomic():
                avaliacao = serializer.save()

        except IntegrityError:
            return Response(
                {
                    "erro": "Você já avaliou este produto."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "mensagem": "Avaliação registrada com sucesso!",
                "avaliacao": AvaliacaoSerializer(
                    avaliacao,
                    context={"request": request}
                ).data
            },
            status=status.HTTP_201_CREATED
        )


# =========================================================
# EDITAR AVALIAÇÃO
# =========================================================

class AvaliacaoDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, id):

        avaliacao = get_object_or_404(
            Avaliacao.objects.select_related(
                "produto",
                "usuario"
            ),
            pk=id,
            usuario=request.user
        )

        # Impede trocar o produto de uma avaliação existente.
        if "produto" in request.data:
            return Response(
                {
                    "erro": (
                        "Não é permitido trocar o produto de uma "
                        "avaliação existente."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AvaliacaoSerializer(
            avaliacao,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if not serializer.is_valid():
            return Response(
                {
                    "erro": "Não foi possível atualizar a avaliação.",
                    "detalhes": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            avaliacao = serializer.save()

        return Response(
            {
                "mensagem": "Avaliação atualizada com sucesso!",
                "avaliacao": AvaliacaoSerializer(
                    avaliacao,
                    context={"request": request}
                ).data
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# CARTEIRA DE FIDELIDADE
# =========================================================

class CarteiraFidelidadeView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        carteira, _ = CarteiraFidelidade.objects.get_or_create(
            usuario=request.user
        )

        selos = carteira.selos

        return Response(
            {
                "carteira": {
                    "usuario": request.user.pk,
                    "selos": selos,
                    "total_selos": TOTAL_SELOS_FIDELIDADE,
                    "progresso": selos,
                    "faltam": max(
                        TOTAL_SELOS_FIDELIDADE - selos,
                        0
                    ),
                    "cartao_completo": (
                        selos >= TOTAL_SELOS_FIDELIDADE
                    ),
                    "criado_em": carteira.criado_em.isoformat(),
                    "atualizado_em": carteira.atualizado_em.isoformat(),
                }
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# LISTAGEM DE CUPONS DO CLIENTE
# =========================================================

class CupomFidelidadeListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        cupons = CupomFidelidade.objects.filter(
            usuario=request.user
        ).order_by("-criado_em")

        todos = [
            serializar_cupom_fidelidade(cupom)
            for cupom in cupons
        ]

        disponiveis = [
            cupom for cupom in todos
            if cupom["status"] == "disponivel"
        ]

        utilizados = [
            cupom for cupom in todos
            if cupom["status"] == "utilizado"
        ]

        return Response(
            {
                "cupons": todos,
                "disponiveis": disponiveis,
                "utilizados": utilizados,
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# VALIDAÇÃO DE CUPOM DO CLIENTE
# =========================================================

class CupomFidelidadeUtilizarView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, codigo):

        cupom = CupomFidelidade.objects.filter(
            usuario=request.user,
            codigo__iexact=codigo.strip()
        ).first()

        if cupom is None:
            return Response(
                {
                    "valido": False,
                    "erro": "Cupom não encontrado."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if cupom.status != "disponivel":
            return Response(
                {
                    "valido": False,
                    "erro": "Este cupom já foi utilizado."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "valido": True,
                "mensagem": "Cupom válido e disponível.",
                "cupom": serializar_cupom_fidelidade(cupom),
            },
            status=status.HTTP_200_OK
        )


# =========================================================
# GERENCIAMENTO DE CUPONS - ADMIN
# =========================================================

class AdminCuponsFidelidadeView(APIView):

    permission_classes = [IsAuthenticated]

    def serializar_cupom_admin(self, cupom):

        usuario = cupom.usuario

        nome_cliente = (
            usuario.get_full_name()
            or getattr(usuario, "username", "")
            or usuario.email
        )

        dados = serializar_cupom_fidelidade(cupom)

        dados.update({
            "usuario_id": usuario.pk,
            "cliente": nome_cliente,
            "email": usuario.email,
        })

        return dados

    def get(self, request):

        if not usuario_e_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para acessar os cupons."
            )

        cupons = (
            CupomFidelidade.objects
            .select_related("usuario")
            .order_by("-criado_em")
        )

        busca = request.query_params.get(
            "busca",
            ""
        ).strip()

        if busca:
            cupons = cupons.filter(
                codigo__icontains=busca
            )

        resultado = [
            self.serializar_cupom_admin(cupom)
            for cupom in cupons
        ]

        return Response(
            {
                "cupons": resultado,
                "total": len(resultado),
                "disponiveis": sum(
                    1 for cupom in resultado
                    if cupom["status"] == "disponivel"
                ),
                "utilizados": sum(
                    1 for cupom in resultado
                    if cupom["status"] == "utilizado"
                ),
            },
            status=status.HTTP_200_OK
        )

    @transaction.atomic
    def patch(self, request, id):

        if not usuario_e_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para alterar os cupons."
            )

        cupom = get_object_or_404(
            CupomFidelidade.objects
            .select_for_update()
            .select_related("usuario"),
            pk=id
        )

        novo_status = request.data.get(
            "status",
            "utilizado"
        )

        if novo_status != "utilizado":
            return Response(
                {
                    "erro": (
                        "O status informado é inválido. "
                        "A ação administrativa permite marcar "
                        "o cupom como utilizado."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if cupom.status == "utilizado":
            return Response(
                {
                    "mensagem": "Este cupom já está marcado como utilizado.",
                    "cupom": self.serializar_cupom_admin(cupom),
                },
                status=status.HTTP_200_OK
            )

        cupom.status = "utilizado"
        cupom.utilizado_em = timezone.now()

        cupom.save(
            update_fields=[
                "status",
                "utilizado_em"
            ]
        )

        return Response(
            {
                "mensagem": "Cupom marcado como utilizado com sucesso!",
                "cupom": self.serializar_cupom_admin(cupom),
            },
            status=status.HTTP_200_OK
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

        return Response(
            {
                "resumo": {
                    "produtos": Produto.objects.count(),
                    "categorias": Categoria.objects.count(),
                    "encomendas": Compra.objects.count(),
                    "usuarios": Usuario.objects.count(),
                    "cupons": CupomFidelidade.objects.count(),
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
            "itens": itens,
            "pagamento_confirmado": compra.pagamento_confirmado,
            "pagamento_confirmado_em": (
                compra.pagamento_confirmado_em.isoformat()
                if compra.pagamento_confirmado_em else None
            ),
            "selo_creditado": compra.selo_creditado,
        }

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

    @transaction.atomic
    def patch(self, request, id):

        if not self.verificar_admin(request):
            return resposta_sem_permissao(
                "Você não tem permissão para alterar as compras."
            )

        compra = get_object_or_404(
            Compra.objects
            .select_for_update()
            .select_related("usuario")
            .prefetch_related("itens__produto"),
            idCompra=id
        )

        dados = request.data

        if not any(
            campo in dados
            for campo in ["status", "pagamento_confirmado"]
        ):
            return Response(
                {
                    "erro": "Informe o status ou a confirmação do pagamento."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        alteracoes = []

        if "status" in dados:

            novo_status = dados.get("status")

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
            alteracoes.append("status")

        resultado_fidelidade = None

        if "pagamento_confirmado" in dados:

            pagamento_confirmado = dados.get(
                "pagamento_confirmado"
            )

            if not isinstance(pagamento_confirmado, bool):
                return Response(
                    {
                        "erro": (
                            "O campo pagamento_confirmado "
                            "deve ser verdadeiro ou falso."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if pagamento_confirmado:

                if compra.status == "cancelado":
                    return Response(
                        {
                            "erro": (
                                "Não é possível confirmar o pagamento "
                                "de uma encomenda cancelada."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if not compra.pagamento_confirmado:

                    compra.pagamento_confirmado = True
                    compra.pagamento_confirmado_em = timezone.now()

                    alteracoes.extend([
                        "pagamento_confirmado",
                        "pagamento_confirmado_em"
                    ])

                resultado_fidelidade = creditar_selo_da_compra(
                    compra
                )

            else:
                compra.pagamento_confirmado = False
                compra.pagamento_confirmado_em = None

                alteracoes.extend([
                    "pagamento_confirmado",
                    "pagamento_confirmado_em"
                ])

        if alteracoes:
            compra.save(
                update_fields=list(set(alteracoes))
            )

        compra.refresh_from_db()

        resposta = {
            "mensagem": "Encomenda atualizada com sucesso.",
            "compra": self.serializar_compra(compra)
        }

        if resultado_fidelidade is not None:

            resposta["fidelidade"] = {
                "creditado": resultado_fidelidade["creditado"],
                "mensagem": resultado_fidelidade["mensagem"],
                "cupom": (
                    serializar_cupom_fidelidade(
                        resultado_fidelidade["cupom"]
                    )
                    if resultado_fidelidade["cupom"]
                    else None
                )
            }

        return Response(
            resposta,
            status=status.HTTP_200_OK
        )
