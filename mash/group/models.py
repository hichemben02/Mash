from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.
User = get_user_model()

class Roomg(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)


class Message(models.Model):
    room = models.ForeignKey(Roomg, on_delete=models.CASCADE, related_name='chats')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_msg')
    text = models.CharField(max_length=300)
    date = models.DateTimeField(auto_now_add=True)