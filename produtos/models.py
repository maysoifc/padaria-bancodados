from django.db import models

class Categoria(models.Model):
    idCategoria = models.AutoField(primary_key=True)
    nome_categoria = models.CharField(max_length=100)

    def __str__(self):
        return self.nome_categoria

class Produto(models.Model):
    idProduto = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    favorito = models.BooleanField(default=False)
    imagem = models.CharField(max_length=255, null=True, blank=True)
    ingredientes_base = models.TextField(null=True, blank=True)
    ingredientes_creme = models.TextField(null=True, blank=True)
    avaliacao = models.FloatField(default=0.0)
    categorias = models.ManyToManyField(Categoria, related_name='produtos')

    def __str__(self):
        return self.nome