import streamlit as st
import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="🧪 Sandbox - Chat Interno SF Pangea", layout="centered")

st.title("💬 Chat Interno de Operaciones")
st.caption("Módulo independiente de prueba para comunicación entre brigadas y administración.")

# --- 1. SIMULADOR DE SESIÓN DE USUARIO ---
st.sidebar.header("⚙️ Configuración de Prueba")
usuario_actual = st.sidebar.selectbox(
    "Simular sesión como:",
    ["Fermín (Admin)", "Brigada Campo 1", "Brigada Campo 2", "Atención Ciudadana"]
)

# --- 2. HISTORIAL TEMPORAL EN MEMORIA ---
if "historial_chat" not in st.session_state:
    # Capturamos la hora exacta de México (UTC-6)
    hora_inicio = datetime.datetime.now(ZoneInfo("America/Mexico_City")).strftime("%I:%M %p")
    st.session_state.historial_chat = [
        {
            "emisor": "Sistema",
            "mensaje": "Bienvenido al canal general de la Dirección de Alumbrado Público.",
            "hora": hora_inicio
        }
    ]

# --- 3. RENDERIZADO DEL HISTORIAL DE MENSAJES ---
chat_container = st.container()

with chat_container:
    for msg in st.session_state.historial_chat:
        es_propio = (msg["emisor"] == usuario_actual)
        avatar_icon = "👨‍💻" if "Admin" in msg["emisor"] else ("🤖" if msg["emisor"] == "Sistema" else "👷‍♂️")
        
        with st.chat_message("user" if es_propio else "assistant", avatar=avatar_icon):
            st.markdown(f"**{msg['emisor']}** <small style='color:gray;'>({msg['hora']})</small>", unsafe_allow_html=True)
            st.write(msg["mensaje"])

# --- 4. ENTRADA DE NUEVO MENSAJE ---
nuevo_mensaje = st.chat_input("Escribe un mensaje para el equipo...")

if nuevo_mensaje:
    # Hora exacta de México al enviar el mensaje
    hora_actual = datetime.datetime.now(ZoneInfo("America/Mexico_City")).strftime("%I:%M %p")
    
    st.session_state.historial_chat.append({
        "emisor": usuario_actual,
        "mensaje": nuevo_mensaje,
        "hora": hora_actual
    })
    st.rerun()
