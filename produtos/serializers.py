
from decimal import Decimal

from rest_framework import serializers

from .models import Produto, Categoria, Compra, ItemCompra


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = [
            "idCategoria",
            "nome_categoria",
        ]


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

        for identificador in data:
            try:
                categoria = Categoria.objects.get(
                    idCategoria=int(identificador)
                )

                categorias.append(categoria)

            except (Categoria.DoesNotExist, ValueError, TypeError):
                raise serializers.ValidationError(
                    f"Categoria inválida: {identificador}."
                )

        return categorias


class ProdutoSerializer(serializers.ModelSerializer):
    categorias = CategoriasProdutoField()

    class Meta:
        model = Produto
        fields = [
            "idProduto",
            "nome",
            "preco",
            "favorito",
            "imagem",
            "categorias",
            "ingredientes_base",
            "ingredientes_creme",
            "avaliacao",
        ]

    def create(self, validated_data):
        categorias = validated_data.pop("categorias", [])

        produto = Produto.objects.create(**validated_data)

        produto.categorias.set(categorias)

        return produto

    def update(self, instance, validated_data):
        categorias = validated_data.pop("categorias", None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        instance.save()

        if categorias is not None:
            instance.categorias.set(categorias)

        return instance


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
        return obj.quantidade * obj.preco_unitario


class CompraSerializer(serializers.ModelSerializer):
    itens = ItemCompraSerializer(many=True, read_only=True)

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
            start=Decimal("0.00"),
        )
