
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count

from rest_framework import serializers

from .models import (
    Produto,
    Categoria,
    Avaliacao,
    Compra,
    ItemCompra,
)


# =========================================================
# CATEGORIAS
# =========================================================

class CategoriaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Categoria
        fields = [
            "idCategoria",
            "nome_categoria",
        ]


# =========================================================
# CAMPO PERSONALIZADO DE CATEGORIAS DO PRODUTO
# =========================================================

class CategoriasProdutoField(serializers.Field):
    """
    Recebe uma lista de IDs de categorias e devolve
    os dados completos das categorias na resposta da API.
    """

    def to_representation(self, value):

        return CategoriaSerializer(
            value.all(),
            many=True
        ).data

    def to_internal_value(self, data):

        if not isinstance(data, list):
            raise serializers.ValidationError(
                "As categorias devem ser enviadas em uma lista."
            )

        categorias = []
        ids_utilizados = set()

        for identificador in data:

            if isinstance(identificador, bool):
                raise serializers.ValidationError(
                    f"Categoria inválida: {identificador}."
                )

            try:
                categoria_id = int(identificador)

                if str(identificador).strip() != str(categoria_id):
                    raise ValueError

                if categoria_id < 1:
                    raise ValueError

                if categoria_id in ids_utilizados:
                    continue

                categoria = Categoria.objects.get(
                    idCategoria=categoria_id
                )

                categorias.append(categoria)
                ids_utilizados.add(categoria_id)

            except (
                Categoria.DoesNotExist,
                ValueError,
                TypeError
            ):
                raise serializers.ValidationError(
                    f"Categoria inválida: {identificador}."
                )

        return categorias


# =========================================================
# PRODUTOS
# =========================================================

class ProdutoSerializer(serializers.ModelSerializer):

    categorias = CategoriasProdutoField()

    preco_com_desconto = serializers.SerializerMethodField()

    quantidade_avaliacoes = serializers.SerializerMethodField()

    class Meta:
        model = Produto

        fields = [
            "idProduto",
            "nome",
            "preco",
            "desconto",
            "preco_com_desconto",
            "favorito",
            "imagem",
            "categorias",
            "ingredientes_base",
            "ingredientes_creme",
            "avaliacao",
            "quantidade_avaliacoes",
        ]

        read_only_fields = [
            "avaliacao",
            "quantidade_avaliacoes",
        ]

    def get_preco_com_desconto(self, obj):

        preco = Decimal(str(obj.preco or "0.00"))
        desconto = Decimal(str(obj.desconto or "0.00"))

        preco_final = preco * (
            Decimal("1.00") - desconto / Decimal("100.00")
        )

        return preco_final.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    def get_quantidade_avaliacoes(self, obj):

        if hasattr(obj, "quantidade_avaliacoes"):
            return obj.quantidade_avaliacoes

        return obj.avaliacoes.count()

    def to_representation(self, instance):
        """
        Exibe a média real das avaliações, sem depender
        de valores antigos ou preenchidos manualmente.
        """

        dados = super().to_representation(instance)

        estatisticas = instance.avaliacoes.aggregate(
            media=Avg("nota"),
            quantidade=Count("id")
        )

        media = estatisticas["media"] or 0

        dados["avaliacao"] = round(float(media), 1)
        dados["quantidade_avaliacoes"] = estatisticas["quantidade"]

        return dados

    def validate_desconto(self, value):

        if value < Decimal("0.00") or value > Decimal("100.00"):
            raise serializers.ValidationError(
                "O desconto deve estar entre 0% e 100%."
            )

        return value

    def create(self, validated_data):

        categorias = validated_data.pop(
            "categorias",
            []
        )

        validated_data.pop("avaliacao", None)

        produto = Produto.objects.create(
            **validated_data
        )

        produto.categorias.set(categorias)

        return produto

    def update(self, instance, validated_data):

        categorias = validated_data.pop(
            "categorias",
            None
        )

        validated_data.pop("avaliacao", None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        instance.save()

        if categorias is not None:
            instance.categorias.set(categorias)

        return instance


# =========================================================
# AVALIAÇÕES
# =========================================================

class AvaliacaoSerializer(serializers.ModelSerializer):

    produto = serializers.PrimaryKeyRelatedField(
        queryset=Produto.objects.all()
    )

    nome_produto = serializers.CharField(
        source="produto.nome",
        read_only=True
    )

    nome_usuario = serializers.CharField(
        source="usuario.username",
        read_only=True
    )

    class Meta:
        model = Avaliacao

        fields = [
            "id",
            "produto",
            "nome_produto",
            "nome_usuario",
            "nota",
            "comentario",
            "criado_em",
        ]

        read_only_fields = [
            "id",
            "nome_usuario",
            "criado_em",
        ]

    def validate_nota(self, value):

        if value < 1 or value > 5:
            raise serializers.ValidationError(
                "A nota deve estar entre 1 e 5."
            )

        return value

    def validate_produto(self, value):

        request = self.context.get("request")

        usuario = (
            request.user
            if request and request.user.is_authenticated
            else None
        )

        if usuario:

            avaliacoes = Avaliacao.objects.filter(
                usuario=usuario,
                produto=value
            )

            # Na edição, ignora a própria avaliação.
            if self.instance:
                avaliacoes = avaliacoes.exclude(
                    pk=self.instance.pk
                )

            if avaliacoes.exists():
                raise serializers.ValidationError(
                    "Você já avaliou este produto."
                )

        return value

    def create(self, validated_data):

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "É necessário estar autenticado para avaliar."
            )

        return Avaliacao.objects.create(
            usuario=request.user,
            **validated_data
        )


# =========================================================
# ITENS DA COMPRA
# =========================================================

class ItemCompraSerializer(serializers.ModelSerializer):

    produto = ProdutoSerializer(
        read_only=True
    )

    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = ItemCompra

        fields = [
            "idItemCompra",
            "produto",
            "quantidade",
            "preco_unitario",
            "subtotal",
        ]

    def get_subtotal(self, obj):

        subtotal = (
            Decimal(str(obj.quantidade))
            * Decimal(str(obj.preco_unitario))
        )

        return subtotal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )


# =========================================================
# COMPRAS
# =========================================================

class CompraSerializer(serializers.ModelSerializer):

    itens = ItemCompraSerializer(
        many=True,
        read_only=True
    )

    total = serializers.SerializerMethodField()

    class Meta:
        model = Compra

        fields = [
            "idCompra",
            "nome",
            "telefone",
            "forma_pagamento",
            "status",
            "criado_em",
            "itens",
            "total",
        ]

        read_only_fields = [
            "idCompra",
            "status",
            "criado_em",
            "itens",
            "total",
        ]

    def get_total(self, obj):

        total = sum(
            (
                Decimal(str(item.quantidade))
                * Decimal(str(item.preco_unitario))
                for item in obj.itens.all()
            ),
            start=Decimal("0.00")
        )

        return total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
