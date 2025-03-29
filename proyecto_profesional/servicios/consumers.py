import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ServicioConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "servicios_updates"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def service_update(self, event):
        await self.send(text_data=json.dumps({
            'service_id': event['service_id'],
            'estado': event['estado'],
        }))

import json
from channels.generic.websocket import AsyncWebsocketConsumer

class OrdenesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "ordenes_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def orden_aceptada(self, event):
        # Envía el mensaje al cliente para que se actualice el tablero
        await self.send(text_data=json.dumps({
            "type": "orden_aceptada",
            "order_id": event["order_id"],
            "order_data": event["order_data"],
        }))

    async def servicio_agregado(self, event):
        # Envía el mensaje al cliente
        await self.send(text_data=json.dumps(event))

    async def orden_reorder(self, event):
        # Envía el evento completo pero asegúrate de que el tipo sea consistente
        mensaje = event.copy()  # Copia el evento para no modificar el original
        # Asegúrate de que tenga un "type"
        if "type" not in mensaje:
            mensaje["type"] = "orden_reorder"
        await self.send(text_data=json.dumps(mensaje))
        
    async def orden_terminada(self, event):
        # Envía el mensaje al cliente
        await self.send(text_data=json.dumps({
            "type": "orden_terminada",
            "order_id": event.get("order_id")
        }))