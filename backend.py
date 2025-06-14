from flask import Flask, request, jsonify
import requests
import os
import json
from datetime import datetime
from urllib.parse import unquote
from answer import Contestation
from router import Router
from _eazyupload_ import eazybase, dbdata
from dotenv import load_dotenv
from twilio.rest import Client
from db_object import DbObject_Elasticsearch
import pytz

load_dotenv()
api_key = os.getenv("api_key")
EAZYBASE_URL = os.getenv("EAZYBASE_URL")
EAZYBASE_TOKEN = os.getenv("EAZYBASE_TOKEN")
COMPANY_OWNER = 12
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

app = Flask(__name__)

router = Router(api_key=api_key)
answer = Contestation(api_key=api_key)
eazybase_ = eazybase(
    register_url_=os.getenv("REGISTER_URL_"),
    login_url=os.getenv("LOGIN_URL"),
    hist_url=os.getenv("HIST_URL"),
    company_=COMPANY_OWNER,
    usr_=os.getenv("USR_"),
    pwd_=os.getenv("PWD_"),
)
dbaccess = dbdata()

location_code_map = {
    "online": "online",
    "Salamanca": "SLM",
    "Santa Marta": "SMR",
    "Bejar": "BJ",
}

availability_map = {
    "online": ["10:00am", "11:00am", "12:00pm", "13:00pm"],
    "SLM": ["10:00am", "11:00am", "12:00pm", "13:00pm"],
    "SMR": ["10:00am", "11:00am", "12:00pm", "13:00pm"],
    "BJ": ["10:00am", "11:00am", "12:00pm", "13:00pm"],
}


def get_options_from_router(router_map):
    where = router_map.get("where")
    how = router_map.get("how")

    # Caso 1: no hay ninguna información
    if not where and not how:
        return availability_map

    # Caso 2: la cita es online
    if not where and how == "online":
        return availability_map[location_code_map["online"]]

    # Caso 3: el lugar es desconocido
    if where == "unknown":
        return str(availability_map)

    # Caso 4: tenemos un lugar concreto
    if where in location_code_map:
        return availability_map[location_code_map[where]]

    # Caso por defecto: devolvemos todas
    return availability_map


@app.route("/create_appointment", methods=["POST"])
def create_appointment():
    try:
        data = request.get_json()
        if not data or "phone" not in data:
            return jsonify({"error": "Faltan campos obligatorios (phone)."}), 400

        phone = data["phone"]
        raw_text = data.get("raw_text", "")
        profile_name = data.get("profile_name", "Usuario")
        assistant_reply = data.get("assistant_reply", "")
        response = eazybase_._register_message(
            inmsg=raw_text,
            outmsg=assistant_reply,
            phone_=phone,
            name_=profile_name,
        )
        if not response or not isinstance(response, dict):
            return (
                jsonify(
                    {
                        "error": "❌ Error desde Eazybase",
                        "status": "no status (bool or error)",
                        "raw": str(response),
                    }
                ),
                500,
            )

    except Exception as e:
        print("❌ Excepción:", str(e))
        return jsonify({"error": f"❌ Excepción: {str(e)}"}), 500


@app.route("/record_appointment", methods=["POST"])
def record_appointment():
    try:
        data = request.get_json()
        phone = data.get("phone")
        location = data.get("location")
        date_ = data.get("date")
        title = data.get("title", f"Reserva presencial de {phone}")
        description = data.get(
            "description",
            f"Se ha confirmado su reserva para el día {date_} en {location}",
        )

        db = DbObject_Elasticsearch()
        doc = {
            "phone": phone,
            "title": title,
            "description": description,
            "date": date_,
            "location": location,
        }
        success = db.insert_value(doc)
        if success:
            return jsonify({"message": "✅ Reserva guardada correctamente"}), 200
        else:
            return jsonify({"error": "❌ Error al guardar reserva"}), 500
    except Exception as e:
        print(f"❌ Error en record_appointment: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/delete_appointment", methods=["POST"])
def delete_appointment():
    data = request.json
    phone = data.get("phone")
    date = data.get("date")
    if not phone or not date:
        return (
            jsonify({"success": False, "error": "phone y date son obligatorios"}),
            400,
        )

    db = DbObject_Elasticsearch()
    success = db.delete_reservation(phone, date)
    if success:
        return jsonify({"success": True, "msg": "Reserva eliminada"})
    else:
        return jsonify({"success": False, "msg": "No se pudo eliminar"}), 404


@app.route("/getwhatsappmessage", methods=["POST"])
def getwamessage():
    conversation = []
    arguments = request.get_json()
    phone_ = arguments.get("From_").replace("whatsapp:", "")
    name_ = arguments.get("ProfileName_")
    text_ = arguments.get("Body_").replace("+", " ")

    # Obtener historial de conversación
    array_usr_hist = eazybase_._get_hist_messages(phone_=phone_, name_=name_)
    for conv_ in array_usr_hist["messages_lst"]:
        conversation.append({"role": "user", "content": conv_["inmsg_ds"]})
        conversation.append({"role": "assistant", "content": conv_["outmsg_ds"]})

    # Obtener eventos futuros y pasados
    db = DbObject_Elasticsearch()
    now = datetime.now(pytz.timezone("Europe/Madrid"))
    now_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    future_events = db.get_future_events(phone_, now_str)
    past_events = db.get_past_events(phone_, now_str)

    if future_events:
        reserva = future_events[
            0
        ]  # solo cogemos la primera, si solo puede haber una activa
        mensaje = (
            f"Tienes una reserva pendiente:\n"
            f"- Fecha y hora: {reserva.get('date','')}\n"
            f"- Lugar: {reserva.get('location','')}\n"
            "\n¿Quieres *anularla*, *modificarla* o hacer una *nueva* reserva? "
            "Por favor, indícalo con una de esas opciones."
        )
        # Enviar mensaje por WhatsApp con Twilio
        try:
            print(f"📞 Enviando WhatsApp a {phone_} (ya tiene reserva activa)")
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            msg = client.messages.create(
                from_=TWILIO_FROM_NUMBER, to=f"whatsapp:{phone_}", body=mensaje
            )
            print(f"✅ WhatsApp enviado correctamente. SID: {msg.sid}")
            return (
                jsonify({"status": "✅ WhatsApp enviado (reserva activa detectada)"}),
                200,
            )
        except Exception as e:
            print(f"❌ Error enviando WhatsApp: {str(e)}")
            return jsonify({"error": f"❌ Error enviando WhatsApp: {str(e)}"}), 500

    # --- SI NO HAY RESERVA FUTURA: sigue flujo normal
    routing_response = router.route(
        conversation,
        list(location_code_map.keys()),
        text_,
        future_events=future_events,
        past_events=past_events,
    )
    final_text = answer.get_response(
        conversation, routing_response, get_options_from_router(routing_response), text_
    )

    # Registrar mensaje en Eazybase
    eazybase_._register_message(
        inmsg=text_, outmsg=final_text, phone_=phone_, name_=name_
    )

    # Enviar mensaje por WhatsApp con Twilio
    try:
        print(f"📞 Enviando WhatsApp a {phone_}")
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            from_=TWILIO_FROM_NUMBER, to=f"whatsapp:{phone_}", body=final_text
        )
        print(f"✅ WhatsApp enviado correctamente. SID: {msg.sid}")
        print(f"📞 FIN ENVIO WhatsApp a {phone_}")
        return jsonify({"status": "✅ WhatsApp enviado"}), 200
    except Exception as e:
        print(f"❌ Error enviando WhatsApp: {str(e)}")
        return jsonify({"error": f"❌ Error enviando WhatsApp: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=True)
