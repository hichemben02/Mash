from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Room, Chat
from django.db.models import Q
from friend.models import FriendList
#from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from cryptography.fernet import Fernet
import os

User = get_user_model()

@login_required
def room_enroll(request):
    friends = FriendList.objects.filter(user=request.user)[0].friends.all()
    all_rooms = Room.objects.filter(
        Q(author=request.user) | Q(friend=request.user)
    ).order_by('-created')

    context = {
        'all_rooms':all_rooms,
        'all_friends':friends,
    }
    return render(request, 'chat/join_room.html', context)



@login_required
def room_choice(request, friend_id):
    friend = User.objects.filter(pk=friend_id)
    if not friend:
        messages.error(request, 'Invalid User ID')
        return redirect('room-enroll') 
    if not FriendList.objects.filter(user=request.user, friends=friend[0]):
        messages.error(request, 'You need to be friends to chat')
        return redirect('room-enroll') 

    room = Room.objects.filter(
        Q(author=request.user, friend=friend[0]) | Q(author=friend[0], friend=request.user)
    )
    if not room:
        create_room = Room(author=request.user, friend=friend[0])
        create_room.save()
        room = create_room.room_id
        return redirect('room', room, friend_id)

    return redirect('room', room[0].room_id, friend_id)


# Chatroom between users
@login_required
def room(request, room_name, friend_id):
    all_rooms = Room.objects.filter(room_id=room_name)
    if not all_rooms:  
        messages.error(request, 'Invalid Room ID')
        return redirect('room-enroll')

    key1 = os.getenv('SECRET_KEY1').encode()
    key2 = os.getenv('SECRET_KEY2').encode()
    cipher = Fernet(key1)
    cipher2 = Fernet(key2)

    chats = Chat.objects.filter(
        room_id=room_name
    ).order_by('date')

    for i in range(len(chats)):
            chats[i].text = cipher.decrypt(chats[i].text.encode()).decode()
            chats[i].text = cipher2.decrypt(chats[i].text.encode()).decode()

    context = {
        'old_chats':chats,
        'my_name':request.user,
        'friend_name':User.objects.get(pk=friend_id),
        'room_name': room_name
    }
    return render(request, 'chat/chatroom.html', context)