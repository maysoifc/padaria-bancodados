from rest_framework import serializers
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):

    class Meta:
        model = Usuario
        fields = (
            'id',
            'username',
            'email',
            'password',
            'foto_perfil',
        )

        extra_kwargs = {
            'password': {
                'write_only': True,
                'required': False
            }
        }

    def create(self, validated_data):
        password = validated_data.pop('password')

        user = Usuario(
            username=validated_data.get('username'),
            email=validated_data.get('email'),
            foto_perfil=validated_data.get('foto_perfil')
        )

        user.set_password(password)
        user.save()

        return user

    def update(self, instance, validated_data):

        instance.username = validated_data.get(
            'username',
            instance.username
        )

        instance.email = validated_data.get(
            'email',
            instance.email
        )

        if 'foto_perfil' in validated_data:
            instance.foto_perfil = validated_data['foto_perfil']

        instance.save()

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)

        try:
            data['foto_perfil'] = (
                instance.foto_perfil.url
                if instance.foto_perfil
                else None
            )
        except Exception:
            data['foto_perfil'] = None

        return data