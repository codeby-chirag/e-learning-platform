import json

from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    # Wakes up the exact millisecond a student opens the webpage
    async def connect(self):
        self.user = self.scope["user"]
        
        # Security: Only allow authenticated logged-in students to connect
        if self.user.is_authenticated:
            # Create a distinct personal broadcast room name just for this specific user
            self.user_room = f"user_{self.user.id}"
            
            # Create a global room name where everyone receives public course launches
            self.global_room = "global_announcements"

            # Accept the open connection line and join both communication rooms
            await self.channel_layer.group_add(self.user_room, self.channel_name)
            await self.channel_layer.group_add(self.global_room, self.channel_name)
            await self.accept()
        else:
            # Deny entry immediately if anonymous
            await self.close()

    # Cleans up memory when a student closes their tab or browser window
    async def disconnect(self, close_code):
        if hasattr(self, 'user_room'):
            await self.channel_layer.group_discard(self.user_room, self.channel_name)
            await self.channel_layer.group_discard(self.global_room, self.channel_name)

    # Intercepts real-time events sent by Django and ships them out to the browser
    async def send_notification(self, event):
        # Extract the message data string dictionary payload
        message = event['message']
        notification_type = event['notification_type']

        # Convert the raw data into JSON strings and push down the socket pipe
        await self.send(text_data=json.dumps({
            'message': message,
            'type': notification_type
        }))
