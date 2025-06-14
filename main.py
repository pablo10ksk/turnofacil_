import streamlit as st
import os
import requests
from router import Router
from answer import Contestation
from backend import location_code_map, get_options_from_router
from dotenv import load_dotenv
from db_object import DbObject_Elasticsearch
import pytz
from datetime import datetime

load_dotenv()
api_key = os.getenv("api_key")


def save_message_to_backend(phone, in_msg="", out_msg=""):
    payload = {
        "phone": phone,
        "raw_text": in_msg,
        "assistant_reply": out_msg,
        "profile_name": "Usuario",
    }
    try:
        res = requests.post("http://localhost:5555/create_appointment", json=payload)
        return res.status_code == 200, res.json()
    except Exception as e:
        return False, {"error": str(e)}


def main():
    st.title("TurnoFácil: gestión de citas")
    user_phone = os.getenv("user_phone")

    if "messages" not in st.session_state:
        st.session_state["messages"] = []
        st.session_state["router"] = Router(api_key=api_key)
        st.session_state["contestation"] = Contestation(api_key=api_key)
    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []

    if not st.session_state["messages"]:
        welcome = "¡Hola! Soy TurnoFácil. ¿Quieres reservar una cita?"
        st.session_state["messages"].append({"role": "assistant", "content": welcome})
        st.session_state["conversation_history"].append(
            {"role": "assistant", "content": welcome}
        )

    # Siempre consulta reservas pasadas y futuras en cada turno
    db = DbObject_Elasticsearch()
    now = datetime.now(pytz.timezone("Europe/Madrid"))
    now_str = now.strftime("%Y-%m-%dT%H:%M:%S")
    future_events = db.get_future_events(user_phone, now_str)
    past_events = db.get_past_events(user_phone, now_str)

    # Si quieres informar al usuario (solo como ejemplo, puedes quitar esto si no lo quieres)
    if future_events:
        reserva = future_events[0]
        mensaje = (
            f"NOTA: Tienes una reserva pendiente:\n"
            f"- Fecha y hora: {reserva.get('date','')}\n"
            f"- Lugar: {reserva.get('location','')}\n"
        )
        # Solo muestra el mensaje una vez (no repetir cada turno)
        if mensaje not in [m["content"] for m in st.session_state["messages"]]:
            st.session_state["messages"].append(
                {"role": "assistant", "content": mensaje}
            )
            st.session_state["conversation_history"].append(
                {"role": "assistant", "content": mensaje}
            )

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Escribe aquí...")

    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.session_state["conversation_history"].append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.markdown(user_input)

        routing_response = st.session_state["router"].route(
            st.session_state["conversation_history"],
            list(location_code_map.keys()),
            user_input,
            future_events=future_events,
            past_events=past_events,
        )

        # Si la intención es cerrar la cita, registra la reserva (como antes)
        if routing_response.get("purpose") == "close":
            payload = {
                "phone": user_phone,
                "location": routing_response.get("where"),
                "date": routing_response.get("when"),
            }
            requests.post(
                "http://localhost:5555/record_appointment", json=payload
            )  # TODO: Change port

        final_text = st.session_state["contestation"].get_response(
            st.session_state["conversation_history"],
            routing_response,
            get_options_from_router(routing_response),
            user_input,
            future_events=future_events,
            past_events=past_events,
        )

        save_message_to_backend(phone=user_phone, in_msg=user_input, out_msg=final_text)

        with st.chat_message("assistant"):
            st.markdown(final_text)
        st.session_state["messages"].append(
            {"role": "assistant", "content": final_text}
        )
        st.session_state["conversation_history"].append(
            {"role": "assistant", "content": final_text}
        )


if __name__ == "__main__":
    main()
