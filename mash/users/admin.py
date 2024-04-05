from django.contrib import admin
from .models import Profile, Relationship, CustomUser

# Register your models here.

admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Relationship)