from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from group.models import Roomg, Message
from cryptography.fernet import Fernet
import os

# Create your views here.
User = get_user_model()

@login_required
def groups(request):
    groups = Roomg.objects.all()
    return render(request, 'group/groups.html', {'groups': groups})

@login_required
def group(request, slug):
    group = Roomg.objects.get(slug=slug)
    chats = Message.objects.filter(room=group).order_by('date')

    key1 = os.getenv('SECRET_KEY1').encode()
    key2 = os.getenv('SECRET_KEY2').encode()
    cipher = Fernet(key1)
    cipher2 = Fernet(key2)

    for i in range(len(chats)):
        chats[i].text = cipher.decrypt(chats[i].text.encode()).decode()
        chats[i].text = cipher2.decrypt(chats[i].text.encode()).decode()
    
    return render(request, 'group/chatgroups.html', {'group': group, 'chats': chats})

def addgroup(request):
    return render(request, 'group/add_group.html')

def checkview(request):
    name = request.POST['name']
    slug = request.POST['slug']

    #check if the room is already exits
    if Roomg.objects.filter(name=name).exists():
        return redirect('group', slug=slug)
    else:
        new_name = Roomg.objects.create(name=name, slug=slug)
        new_name.save()
        return redirect('group', slug=slug)