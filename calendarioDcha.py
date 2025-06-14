import streamlit as st
from streamlit_calendar import calendar
from db_object import DbObject_Elasticsearch
from dateutil import parser
from datetime import timedelta

st.set_page_config(page_title="Calendario de Reservas", layout="wide")

st.markdown("""
<style>
.fc-event-title, .fc-event-main {
    font-size: 16px !important;
    padding: 6px 0 !important;
    min-height: 32px !important;
    cursor: pointer !important;
}
.fc-daygrid-event {
    min-height: 32px !important;
    cursor: pointer !important;
}
</style>
""", unsafe_allow_html=True)

st.title("Calendario de reservas (TurnoFácil)")

db = DbObject_Elasticsearch()

phone = st.text_input("Introduce el teléfono para filtrar reservas (opcional):").strip()
if phone:
    reservas = db.search_(phone)
else:
    reservas = db.get_all_reservations()

eventos = []
for reserva in reservas:
    r = reserva["_source"]
    eventos.append({
        "id": reserva["_id"],
        "title": r.get("title", "Reserva"),
        "start": r.get("date"),
        "end": r.get("date"),
        "allDay": False,
        "extendedProps": {
            "location": r.get("location", ""),
            "description": r.get("description", ""),
            "phone": r.get("phone", ""),
        },
    })

col1, col2 = st.columns([2, 1])

with col1:
    cal = calendar(
        events=eventos,
        options={
            "editable": False,
            "selectable": True,
            "initialView": "dayGridMonth",
            "locale": "es",
            "eventClick": True,
        },
        key=f"calendar_turnofacil_{phone}"
    )
    if cal and cal.get("callback") == "dateClick":
        date_str = cal["dateClick"]["date"]
        clicked_day = parser.parse(date_str).date()
        st.session_state["fecha_clickada"] = clicked_day


with col2:
    st.subheader("Reservas del día seleccionado")
    fecha_clickada = st.session_state.get("fecha_clickada", None)
    if fecha_clickada:
        fecha_clickada = fecha_clickada + timedelta(days=1)  # Sumar 1 día

    # Siempre filtra reservas en tiempo real según la fecha seleccionada
    reservas_dia = []
    if fecha_clickada:
        for ev in eventos:
            ev_day = parser.parse(ev["start"]).date()
            if ev_day == fecha_clickada:
                reservas_dia.append(ev)
        st.write(f"Fecha seleccionada: **{fecha_clickada.strftime('%d/%m/%Y')}**")

    if reservas_dia:
        for ev in reservas_dia:
            st.markdown(f"""
                <div style="background-color:#f6f6f9;padding:16px;margin-bottom:10px;border-radius:16px;border:1px solid #d0d2d6;">
                    <b>Título:</b> {ev.get('title', '')}<br>
                    <b>Fecha y hora:</b> {ev.get('start', '')}<br>
                    <b>Lugar:</b> {ev.get('extendedProps', {}).get('location', '')}<br>
                    <b>Teléfono:</b> {ev.get('extendedProps', {}).get('phone', '')}<br>
                    <b>Descripción:</b> {ev.get('extendedProps', {}).get('description', '')}
                </div>
            """, unsafe_allow_html=True)
    elif fecha_clickada:
        st.info("No hay reservas para este día. Haz click en otro día para consultar.")
    else:
        st.info("Haz click en un día para ver sus reservas.")
