
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from .models import Produto, Categoria, Compra, ItemCompra


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

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        instance.save()

        if categorias is not None:
            instance.categorias.set(categorias)

        return instance


# =========================================================
# ITENS DA COMPRA
# =========================================================

class ItemCompraSerializer(serializers.ModelSerializer):

    produto = ProdutoSerializer(read_only=True)

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

        return (
            obj.quantidade * obj.preco_unitario
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

    def get_total(self, obj):

        return sum(
            (
                item.quantidade * item.preco_unitario
                for item in obj.itens.all()
            ),
            start=Decimal("0.00")
        )
