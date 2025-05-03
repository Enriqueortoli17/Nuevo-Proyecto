# utils.py
import os
from twilio.rest import Client


def send_whatsapp_message(to_phone, message_body):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise Exception("Las credenciales de Twilio no están configuradas.")

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=message_body,
        from_="whatsapp:+14155238886",  # Cambia este valor por tu número de WhatsApp configurado en Twilio
        to=f"whatsapp:{to_phone}",
    )
    return message.sid
