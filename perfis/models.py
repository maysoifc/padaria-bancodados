from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField

class Usuario(AbstractUser):
    email = models.EmailField(unique=True)
    foto_perfil = CloudinaryField('image', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email