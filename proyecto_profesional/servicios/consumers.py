import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ServicioConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "servicios_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def service_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "service_id": event["service_id"],
                    "estado": event["estado"],
                }
            )
        )


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
        await self.send(
            text_data=json.dumps(
                {
                    "type": "orden_aceptada",
                    "order_id": event["order_id"],
                    "order_data": event["order_data"],
                }
            )
        )

    async def servicio_agregado(self, event):
        # Envía el mensaje al cliente
        await self.send(text_data=json.dumps(event))

    # MÉTODO PARA MANEJAR ACTUALIZACIONES DE ESTADO GENERAL (ej. a PROCESO)
    async def orden_update(self, event):
        """
        Manejador para cuando el estado general de una orden cambia (ej. a PROCESO).
        """
        print(f"DEBUG [Consumer]: Recibido evento 'orden_update': {event}") # Añadido para verificar
        order_id = event.get('order_id')
        nuevo_estado = event.get('nuevo_estado')

        if order_id:
            print(f"DEBUG [Consumer]: Enviando mensaje 'orden_update' al frontend para orden {order_id} con estado {nuevo_estado}") # Añadido para verificar
            await self.send(text_data=json.dumps({
                'type': 'orden_update',
                'order_id': order_id,
                'nuevo_estado': nuevo_estado
            }))
        else:
             print("DEBUG WARN [Consumer]: Evento 'orden_update' recibido sin 'order_id'")

    async def orden_reorder(self, event):
        # Envía el evento completo pero asegúrate de que el tipo sea consistente
        mensaje = event.copy()  # Copia el evento para no modificar el original
        # Asegúrate de que tenga un "type"
        if "type" not in mensaje:
            mensaje["type"] = "orden_reorder"
        await self.send(text_data=json.dumps(mensaje))

    async def orden_terminada(self, event):
        """
        Manejador para cuando una orden cambia su estado general a LISTO.
        Recibe el evento del grupo 'ordenes_updates' y envía un mensaje
        al cliente WebSocket para que elimine la orden del tablero.
        """
        # --- Debugging ---
        print(f"DEBUG [Consumer]: Recibido evento 'orden_terminada': {event}")
        # --- Fin Debugging ---

        order_id = event.get('order_id')

        if order_id:
            # --- Debugging ---
            print(f"DEBUG [Consumer]: Enviando mensaje 'orden_terminada' al frontend para orden {order_id}")
            # --- Fin Debugging ---

            # Enviar mensaje al WebSocket individual
            await self.send(text_data=json.dumps({
                'type': 'orden_terminada', # Coincide con el tipo esperado por el JS
                'order_id': order_id
            }))
        else:
             print("DEBUG WARN [Consumer]: Evento 'orden_terminada' recibido sin 'order_id'")
        
