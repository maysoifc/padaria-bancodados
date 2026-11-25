
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    foto_perfil = serializers.ImageField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "email",
            "password",
            "foto_perfil",
        )
        extra_kwargs = {
            "password": {
                "write_only": True,
                "required": False,
            }
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.foto_perfil:
            try:
                data["foto_perfil"] = instance.foto_perfil.url
            except (ValueError, AttributeError):
                data["foto_perfil"] = None
        else:
            data["foto_perfil"] = None

        return data

    def create(self, validated_data):
        password = validated_data.pop("password", None)

        if not password:
            raise serializers.ValidationError({
                "password": "A senha é obrigatória."
            })

        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()

        return user

    def update(self, instance, validated_data):
        instance.username = validated_data.get(
            "username", instance.username
        )

        instance.email = validated_data.get(
            "email", instance.email
        )

        if "foto_perfil" in validated_data:
            instance.foto_perfil = validated_data["foto_perfil"]

        if "password" in validated_data:
            password = validated_data.pop("password")
            if password:
                instance.set_password(password)

        instance.save()

        return instance


class AdminUsuarioSerializer(serializers.ModelSerializer):
    foto_perfil = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "first_name",
            "email",
            "foto_perfil",
            "is_active",
            "is_superuser",
            "date_joined",
        )

    def get_foto_perfil(self, obj):
        if not obj.foto_perfil:
            return None

        try:
            return obj.foto_perfil.url
        except (ValueError, AttributeError):
            return None


class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        if not (
            self.user.is_staff or self.user.is_superuser
        ):
            raise AuthenticationFailed(
                "Esta conta não possui acesso administrativo."
            )

        data["is_admin"] = True
        data["username"] = self.user.username

        return data
