from django.db import models

class Categoria(models.Model):
    idCategoria = models.AutoField(primary_key=True)
    nome_categoria = models.CharField(max_length=100)

    def __str__(self):
        return self.nome_categoria

class Produto(models.Model):
    idProduto = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=200)
    favorito = models.BooleanField(default=False)
    categorias = models.ManyToManyField(Categoria, related_name='produtos')

    def __str__(self):
        return self.nome