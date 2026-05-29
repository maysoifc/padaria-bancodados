from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # Isso garante que a interface administrativa reconheça seus campos
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('email', 'username')