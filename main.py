import streamlit as st
import os
import json
import requests
from router import Router
from answer import Contestation
from backend import location_code_map, availability_map, get_options_from_router
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("api_key")


# 🟡 BACKEND FLASK como intermediario
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

        routing_response = st.session_state.router.route(
            st.session_state["conversation_history"],
            list(location_code_map.keys()),
            user_input,  # Añadido
        )

        if routing_response["purpose"] == "close":
            routing_response["phone"] = user_phone
            res = requests.post(
                "http://localhost:5555/record_apponintment", json=routing_response
            )

        final_text = st.session_state.contestation.get_response(
            st.session_state["conversation_history"],
            routing_response,
            get_options_from_router(routing_response),
            user_input,  # Añadido
        )
        # Enviamos entrada + salida en la misma llamada al backend Flask
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
