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

load_dotenv()
api_key = os.getenv("api_key")
EAZYBASE_URL = os.getenv("EAZYBASE_URL")
EAZYBASE_TOKEN = os.getenv("EAZYBASE_TOKEN")
COMPANY_OWNER = 12

app = Flask(__name__)


router = Router(api_key=api_key)
answer = Contestation(api_key=api_key)
eazybase_ = eazybase(
    register_url_=os.getenv("register_url_"),
    login_url=os.getenv("login_url"),
    hist_url=os.getenv("hist_url"),
    company_=COMPANY_OWNER,
    usr_=os.getenv("usr_"),
    pwd_=os.getenv("pwd_"),
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
    print(router_map)
    print(availability_map)

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
        if not response:
            return (
                jsonify(
                    {
                        "error": f"❌ Error desde Eazybase",
                        "status": response.status_code,
                        "raw": response.text,
                    }
                ),
                500,
            )
        else:
            return jsonify({"message": "✅ Cita registrada en Eazybase."}), 200

    except Exception as e:
        print("❌ Excepción:", str(e))
        return jsonify({"error": f"❌ Excepción: {str(e)}"}), 500


@app.route("/record_apponintment", methods=["POST"])
def record_apponintment():
    data = request.get_json()
    phone = data.get("phone")
    location = data.get("location")
    date_ = data.get("date")
    log = dbaccess.insert_record(phone, date_, location)
    return jsonify(log)


@app.route("/getwhatsappmessage", methods=["POST"])
def getwamessage():
    conversation = []
    arguments = request.get_json()
    phone_ = arguments.get("From_").replace("whatsapp:", "")
    name_ = arguments.get("ProfileName_")
    text_ = arguments.get("Body_").replace("+", " ")

    array_usr_hist = eazybase_._get_hist_messages(phone_=phone_, name_=name_)
    for conv_ in array_usr_hist["messages_lst"]:
        conversation.append({"role": "user", "content": conv_["inmsg_ds"]})
        conversation.append({"role": "assistant", "content": conv_["outmsg_ds"]})

    routing_response = router.route(conversation, list(location_code_map.keys()), text_)
    final_text = answer.get_response(
        conversation, routing_response, get_options_from_router(routing_response), text_
    )
    eazybase_._register_message(
        inmsg=text_, outmsg=final_text, phone_=phone_, name_=name_
    )
    return jsonify(
        {"response": final_text}
    )  # TODO: Aquí hay que enviar un Whatsapp, no contestar a la interfaz


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=True)
