import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import unicodedata

# --- CONFIGURACIÓN ---
# En Render, estas variables se configuran en el panel web por seguridad.
# Pero para probar rápido, puedes ponerlas aquí (aunque no es lo ideal para seguridad).
ACCOUNT_SID = os.environ.get('TWILIO_SID', 'PON_TU_SID_AQUI')
AUTH_TOKEN = os.environ.get('TWILIO_TOKEN', 'PON_TU_TOKEN_AQUI')
# Número que compraste o te dio Twilio (Debe poder recibir SMS y hacer llamadas)
SERVER_PHONE = os.environ.get('TWILIO_NUMBER', 'PON_TU_NUMERO_TWILIO_AQUI') 

app = Flask(__name__)
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Memoria temporal (se reinicia si el servidor duerme, para prod usar base de datos)
user_sessions = {}

class InterviewLogic:
    def __init__(self):
        self.state = "0_SALUDO"

    def normalize(self, text):
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower().strip()

    def process(self, incoming_msg, sender_number):
        msg = self.normalize(incoming_msg)
        response_text = ""
        trigger_call = False

        if self.state == "0_SALUDO":
            response_text = "👋 ¡Hola! Soy el asistente virtual de *Cipriam Company*. Estamos contratando. ¿Tienes experiencia en ventas? (Sí/No)"
            self.state = "WAITING_EXP"
        
        elif self.state == "WAITING_EXP":
            if "si" in msg or "claro" in msg:
                response_text = "Excelente. 🚗 ¿Cuentas con vehículo propio para visitar clientes? (Sí/No)"
                self.state = "WAITING_AUTO"
            else:
                response_text = "Entendido. Por el momento requerimos experiencia previa. Guardaremos tu CV. ¡Gracias!"
                self.state = "END"

        elif self.state == "WAITING_AUTO":
            if "si" in msg:
                response_text = "Perfecto. 🎉 Cumples con el perfil preliminar.\n\n📞 *En unos segundos recibirás una llamada de mi parte* para confirmar tus datos. Atiende por favor."
                trigger_call = True
                self.state = "END"
            else:
                response_text = "Gracias. El puesto requiere movilidad propia. Te avisaremos si abre una vacante administrativa."
                self.state = "END"
        
        return response_text, trigger_call

@app.route("/bot", methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '') # whatsapp:+58...

    if sender not in user_sessions:
        user_sessions[sender] = InterviewLogic()
        # Si es el primer mensaje (o dice Hola), iniciamos
        reply, call = user_sessions[sender].process(incoming_msg, sender)
    else:
        # Continuamos conversación
        reply, call = user_sessions[sender].process(incoming_msg, sender)

    # 1. Responder por Chat
    resp = MessagingResponse()
    resp.message(reply)

    # 2. Hacer la llamada (Si aplica)
    if call:
        clean_number = sender.replace("whatsapp:", "")
        try:
            # TwiML: Instrucciones de qué decir cuando contesten
            twiml_instruction = (
                '<Response>'
                '<Pause length="1"/>'
                '<Say language="es-MX" voice="Polly.Lupe">Hola. Te llamo de Cipriam Company. '
                'Vimos que tienes experiencia y vehículo. Queremos agendarte una entrevista mañana a las 10 de la mañana. '
                'Te enviaremos la dirección por WhatsApp. Hasta luego.</Say>'
                '</Response>'
            )
            
            client.calls.create(
                twiml=twiml_instruction,
                to=clean_number,
                from_=SERVER_PHONE
            )
            print(f"Llamada iniciada a {clean_number}")
        except Exception as e:
            print(f"Error llamando: {e}")

    return str(resp)

if __name__ == "__main__":
    app.run()