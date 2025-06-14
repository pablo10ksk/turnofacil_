from openai import OpenAI
import json
from datetime import datetime
import pytz

# Fecha actual en horario de España
tz = pytz.timezone("Europe/Madrid")
fecha_actual = datetime.now(tz)
fecha_actual_str = fecha_actual.strftime("%A, %d de %B de %Y")


class Contestation:
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def get_response(
        self,
        conversation_history: list[dict],
        routing_data: dict,
        availability: list,
        message_: str,
        future_events: list = None,
        past_events: list = None,
        location_map_pretty={
            "online": "online",
            "SLM": "Salamanca",
            "SMR": "Santa Marta",
            "BJ": "Béjar",
        },
    ):
        future_events = future_events or []
        past_events = past_events or []
        eventos_futuros_text = json.dumps(future_events, ensure_ascii=False, indent=2)
        eventos_pasados_text = json.dumps(past_events, ensure_ascii=False, indent=2)


        """
        Genera una respuesta basada en la conversacion y los datos del router.
        """
        system_message = {
            "role": "system",
            "content": (
                f"""Eres un asistente inteligente para reservar citas. RESPONDE SIEMPRE EN ESPAÑOL.
                "Antes de nada, ten en cuenta que la fecha actual es: {fecha_actual_str}. Usa esta referencia para interpretar expresiones como 'hoy', 'mañana', 'la semana que viene', etc."
                "sigue estrictamente estas reglas:"
                1. ❌ NUNCA preguntes por el propósito de la cita.
                2. ✅ Solo necesitas saber: 
                - modalidad (online/presencial), 
                - ubicación (si es presencial)[NOTA IMPORTANTE: Estos son los códigos de ubicación que recibirás y su significado para que respondas de forma natural:{json.dumps(location_map_pretty, indent=2)}], 
                - fecha y hora.
                3. ✅ Si falta alguno de esos datos, haz una única pregunta clara y cercana para conseguirlo.
                4. ✅ Si el usuario dice "lo antes posible", ofrece la siguiente hora disponible.
                5. ❗ NO puedes cerrar la cita sin la confirmación explícita del usuario.
                6. ✅ Si te da todos los datos, resume y confirma la cita. El mensaje de confirmación debe incluir: 
                        - modalidad (online/presencial),
                        - ubicación (si es presencial: LOCALIDAD EXACTA, CIUDAD O PUEBLO),
                        - fecha y hora EXACTOS.
                7. ❗ Si el lugar no está claro o no es un sitio concreto, ofrece 3 opciones más cercanas.
                8. ❌ Nunca respondas en inglés.
                

                Datos disponibles:
                - Disponibilidad: {availability}
                - Datos del usuario (extraídos por el router):
                - EVENTOS FUTUROS del usuario (reservas pendientes):\n{eventos_futuros_text}
                - EVENTOS PASADOS del usuario (histórico de reservas):\n{eventos_pasados_text}
                {json.dumps(routing_data, indent=2)}
                """
            ),
        }

        full_messages = [system_message] + conversation_history
        full_messages.append({"role": "user", "content": message_})

        response = self.client.chat.completions.create(
            model=self.model, messages=full_messages, temperature=0
        )
        return response.choices[0].message.content
