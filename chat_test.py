import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de la página
st.set_page_config(
    page_title="SF Pangea Chat",
    page_icon="💬",
    layout="centered"
)

st.title("💬 SF Pangea Chat")

# 2. Conexión nativa con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Carga de datos optimizada con caché de 60 segundos
@st.cache_data(ttl=60)
def cargar_historial():
    return conn.read()

# 3. Inicializar Estado de la Sesión para el Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. Prueba de Conexión Inicial
try:
    df_bd = cargar_historial()
    st.success("🟢 Sistema inicializado y conectado a BD_PANGEA")
except Exception as e:
    st.error(f"🔴 Error de conexión con Google Cloud: {e}")
    st.stop()

# 5. Renderizado de Mensajes en Pantalla
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Captura de Entrada del Usuario
if prompt := st.chat_input("Escribe tu mensaje aquí..."):
    # Agregar mensaje del usuario a la pantalla
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta provisional del sistema (Estructura base)
    respuesta = f"Recibido: {prompt}"
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
    with st.chat_message("assistant"):
        st.markdown(respuesta)
