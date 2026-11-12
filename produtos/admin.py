from django.contrib import admin

from .models import (
    Produto,
    Categoria,
    Avaliacao,
    Compra,
    ItemCompra,
)


admin.site.register(Produto)
admin.site.register(Categoria)
admin.site.register(Avaliacao)
admin.site.register(Compra)
admin.site.register(ItemCompra)