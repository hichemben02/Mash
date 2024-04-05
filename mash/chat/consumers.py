from chat.models import Chat, Room
import json
from channels.generic.websocket import AsyncWebsocketConsumer
#from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from cryptography.fernet import Fernet
from asgiref.sync import sync_to_async, async_to_sync
import os

User = get_user_model()

# MESSAGE DB ENTRY
@sync_to_async
def create_new_message(me,friend,message,room_id):
    get_room = Room.objects.filter(room_id=room_id)[0]
    author_user = User.objects.filter(username=me)[0]
    friend_user = User.objects.filter(username=friend)[0]
    new_chat = Chat.objects.create(
        author=author_user,
        friend=friend_user,
        room_id=get_room,
        text=message)
        

class ChatRoomConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #self.key = os.getenv('SECRET_KEY')
        #print(self.key)
        self.cipher = Fernet(b'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=')
        #self.keysocket = os.getenv('SECRET_KEY2')
        self.ciphersocket = Fernet(b'W4q6yj1bELzo7s7kwqxHLb_ceddPjiBJTTcBfZjPuK4=')

    # Connect
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    # Disconnect
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )


    def encrypt_message(self, message):
        return self.cipher.encrypt(message.encode()).decode()

    def decrypt_message(self, encrypted_message):
        return self.cipher.decrypt(encrypted_message.encode()).decode()

    # Receive
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        message2 = self.ciphersocket.encrypt(message.encode()).decode()
        print(f"=============Message from websocket ==> {message2}===================")
        username = text_data_json['username']
        user_image = text_data_json['user_image']

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chatroom_message',
                'message': message2,
                'username': username,
                'user_image': user_image,
            }
        )



    # Messages
    async def chatroom_message(self, event):
        message = event['message']
        message2 = self.ciphersocket.decrypt(message.encode()).decode()
        print(f"=============Message to websocket ==> {message2}===================")
        encrypted_message = self.encrypt_message(message)
        username = event['username']
        user_image = event['user_image']

        await create_new_message(me=self.scope["user"], friend=username, message=encrypted_message, room_id=self.room_name)
        
        await self.send(text_data=json.dumps({
            'message': message2,
            'username': username,
            'user_image': user_image,
        }))