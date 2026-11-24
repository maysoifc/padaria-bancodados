
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# =========================================================
# CATEGORIAS
# =========================================================

class Categoria(models.Model):
    idCategoria = models.AutoField(primary_key=True)

    nome_categoria = models.CharField(
        max_length=100
    )

    def __str__(self):
        return self.nome_categoria

    class Meta:
        ordering = ["nome_categoria"]
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"


# =========================================================
# PRODUTOS
# =========================================================

class Produto(models.Model):
    idProduto = models.AutoField(primary_key=True)

    nome = models.CharField(
        max_length=200
    )

    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[
            MinValueValidator(0)
        ]
    )

    # DESCONTO EM PORCENTAGEM
    desconto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        verbose_name="Desconto (%)"
    )

    favorito = models.BooleanField(
        default=False
    )

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

    # Média das avaliações do produto.
    # Será atualizada pelas operações de avaliação.
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

    @property
    def preco_com_desconto(self):
        return self.preco * (
            1 - self.desconto / 100
        )

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ["nome"]
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"


# =========================================================
# AVALIAÇÕES
# =========================================================

class Avaliacao(models.Model):

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
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

    comentario = models.TextField(
        blank=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "produto"],
                name="uma_avaliacao_por_usuario_produto"
            )
        ]

        ordering = ["-criado_em"]

        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"

    def __str__(self):
        return (
            f"{self.usuario} - "
            f"{self.produto} - "
            f"{self.nota}"
        )


# =========================================================
# COMPRAS
# =========================================================

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
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="compras"
    )

    nome = models.CharField(
        max_length=200
    )

    telefone = models.CharField(
        max_length=20
    )

    forma_pagamento = models.CharField(
        max_length=20
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente"
    )

    # CONFIRMAÇÃO DO PAGAMENTO

    pagamento_confirmado = models.BooleanField(
        default=False,
        verbose_name="Pagamento confirmado"
    )

    pagamento_confirmado_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data da confirmação do pagamento"
    )

    # CONTROLE DE CRÉDITO DE SELO

    selo_creditado = models.BooleanField(
        default=False,
        verbose_name="Selo creditado"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Compra #{self.idCompra} - {self.usuario}"

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Compra"
        verbose_name_plural = "Compras"


# =========================================================
# CARTEIRA DE FIDELIDADE
# =========================================================

class CarteiraFidelidade(models.Model):

    TOTAL_SELOS = 10

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carteira_fidelidade"
    )

    selos = models.PositiveSmallIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(TOTAL_SELOS)
        ],
        verbose_name="Quantidade de selos"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    @property
    def progresso(self):
        return min(
            (self.selos / self.TOTAL_SELOS) * 100,
            100
        )

    @property
    def faltam(self):
        return max(
            self.TOTAL_SELOS - self.selos,
            0
        )

    @property
    def cartao_completo(self):
        return self.selos >= self.TOTAL_SELOS

    def __str__(self):
        return (
            f"Carteira de {self.usuario} - "
            f"{self.selos}/{self.TOTAL_SELOS}"
        )

    class Meta:
        verbose_name = "Carteira de fidelidade"
        verbose_name_plural = "Carteiras de fidelidade"


# =========================================================
# CUPONS DE FIDELIDADE
# =========================================================

class CupomFidelidade(models.Model):

    STATUS_CHOICES = [
        ("disponivel", "Disponível"),
        ("utilizado", "Utilizado"),
    ]

    TIPO_CHOICES = [
        ("produto", "Produto grátis"),
        ("desconto", "Desconto"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cupons_fidelidade"
    )

    codigo = models.CharField(
        max_length=30,
        unique=True
    )

    titulo = models.CharField(
        max_length=150
    )

    descricao = models.TextField()

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES
    )

    icone = models.CharField(
        max_length=100,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="disponivel"
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    utilizado_em = models.DateTimeField(
        null=True,
        blank=True
    )

    compra = models.ForeignKey(
        Compra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cupons_utilizados"
    )

    def __str__(self):
        return (
            f"{self.codigo} - "
            f"{self.titulo} - "
            f"{self.usuario}"
        )

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Cupom de fidelidade"
        verbose_name_plural = "Cupons de fidelidade"


# =========================================================
# ITENS DA COMPRA
# =========================================================

class ItemCompra(models.Model):

    idItemCompra = models.AutoField(primary_key=True)

    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="itens"
    )

    # Preserva o histórico das compras.
    # Produtos utilizados em compras não poderão ser excluídos.
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="itens_comprados"
    )

    quantidade = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1)
        ]
    )

    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0)
        ]
    )

    def __str__(self):
        return f"{self.produto.nome} - {self.quantidade}x"

    class Meta:
        verbose_name = "Item da compra"
        verbose_name_plural = "Itens das compras"
