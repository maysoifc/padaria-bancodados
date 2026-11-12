
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Categoria(models.Model):
    idCategoria = models.AutoField(primary_key=True)
    nome_categoria = models.CharField(max_length=100)

    def __str__(self):
        return self.nome_categoria


class Produto(models.Model):
    idProduto = models.AutoField(primary_key=True)

    nome = models.CharField(max_length=200)

    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )

    favorito = models.BooleanField(default=False)

    imagem = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    ingredientes_base = models.TextField(
        null=True,
        blank=True
    )

    ingredientes_creme = models.TextField(
        null=True,
        blank=True
    )

    avaliacao = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(5)
        ]
    )

    categorias = models.ManyToManyField(
        Categoria,
        related_name="produtos"
    )

    def __str__(self):
        return self.nome


class Avaliacao(models.Model):
    usuario = models.ForeignKey(
        "perfis.Usuario",
        on_delete=models.CASCADE,
        related_name="avaliacoes"
    )

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="avaliacoes"
    )

    nota = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    comentario = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "produto"],
                name="uma_avaliacao_por_usuario_produto"
            )
        ]
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.usuario} - {self.produto} - {self.nota}"


class Compra(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("preparando", "Em preparação"),
        ("pronto", "Pronto para retirada"),
        ("finalizado", "Finalizado"),
        ("cancelado", "Cancelado"),
    ]

    idCompra = models.AutoField(primary_key=True)

    usuario = models.ForeignKey(
        "perfis.Usuario",
        on_delete=models.CASCADE,
        related_name="compras"
    )

    nome = models.CharField(max_length=200)

    telefone = models.CharField(max_length=20)

    forma_pagamento = models.CharField(max_length=20)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente"
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Compra #{self.idCompra} - {self.usuario}"


class ItemCompra(models.Model):
    idItemCompra = models.AutoField(primary_key=True)

    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="itens"
    )

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="itens_comprados"
    )

    quantidade = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return f"{self.produto.nome} - {self.quantidade}x"
