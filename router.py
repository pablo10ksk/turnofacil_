from openai import OpenAI
import json
from datetime import datetime, timedelta
from datetime import datetime, timedelta
import pytz


# ================== 0. Configuración de fechas ==================
tz = pytz.timezone("Europe/Madrid")
fecha_actual = datetime.now(tz)
fecha_actual_str = fecha_actual.strftime(
    "%A, %d de %B de %Y"
)  # Ej: jueves, 10 de abril de 2025
fecha_manana = fecha_actual + timedelta(days=1)
manana_str = fecha_manana.strftime("%Y-%m-%dT10:00:00")  # Ej: 2025-04-11T10:00:00


# ========= 1. Definir clases ===============
class Router:
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def route(self, conversation_history, locations, current_msg):
        messages_for_router = (
            [
                {
                    "role": "system",
                    "content": (
                        f"Tu tarea es extraer información en formato JSON sobre la cita que el usuario quiere reservar.\n"
                        f"La fecha actual es: {fecha_actual}. Interpreta expresiones como 'mañana', 'la semana que viene' o 'pasado mañana' teniendo en cuenta esta fecha.\n"
                        "⚠️ Si el usuario **NO indica explícitamente** que quiere una cita online o presencial, NO rellenes el campo 'how'.\n"
                        "⚠️ Solo incluye 'how' si el usuario usa palabras como 'online', 'en persona', 'presencial', etc. (sinónimos de ellas)\n"
                        "⚠️ Solo incluye 'where' si el usuario dice una localidad clara (CIUDAD o PUEBLO: como Salamanca, Bejar, etc.). Si no es concreta, sigue preguntando hasta dar con el lugar exacto\n"
                        "⚠️ Si no puedes deducir algún dato con seguridad, NO lo pongas en el JSON.\n"
                        "⚠️ Hasta que no tengas los datos CONCRETOS de -how-, -where-, -when- el purpose seguirá siendo research. Solo cambiará a close cuando ya tengas los tres campos 100% seguros.\n"
                        "Devuelve únicamente un objeto JSON válido. No pongas explicaciones ni código ni comillas alrededor del JSON.\n"
                        "Ejemplos válidos:\n"
                        '- Usuario dice: \'quiero una cita online mañana\' → {"purpose": "research", "how": "online"}\n'
                        '- Usuario dice: \'quiero una cita\' → {"purpose": "research"}\n'
                        f'- Usuario dice: \'en salamanca mañana a las 10\' → {{"purpose": "close", "how": "presencial", "where": "Salamanca", "when": "{manana_str}"}}\n'
                    ),
                }
            ]
            + conversation_history
            + [
                {
                    "role": "user",
                    "content": (
                        f'Conversation so far (user and system messages): "{current_msg}".\n\n'
                        "Return ONLY the JSON object. No extra text."
                    ),
                },
            ]
        )
        print(messages_for_router)
        json_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "router",
                "schema": {
                    "type": "object",
                    "properties": {
                        "purpose": {
                            "type": "string",
                            "enum": ["close", "research"],
                            "description": "if the message of the user imples to continue with the conversation or just to finish it",
                        },
                        "how": {
                            "type": "string",
                            "enum": ["physical", "online"],
                            "description": "If the meeting should be online or physical",
                        },
                        "where": {
                            "type": "string",
                            "enum": locations,
                            "description": "requested location of the user. If online, then online, if unknown then unknown",
                        },
                    },
                    "required": ["purpose", "how"],
                },
            },
        }
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages_for_router,
            temperature=0,
            response_format=json_schema,
        )
        content = response.choices[0].message.content

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
