import streamlit as st
import datetime
import uuid
import re
from zoneinfo import ZoneInfo

st.set_page_config(page_title="💬 SF Pangea Chat - Sandbox", layout="wide")

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.title("💬 SF Pangea Chat")

# Hora local de México
def obtener_hora_mexico():
    return datetime.datetime.now(ZoneInfo("America/Mexico_City")).strftime("%I:%M %p")

# Lista de usuarios del sistema
USUARIOS = ["Fermín (Admin)", "Brigada Campo 1", "Brigada Campo 2", "Atención Ciudadana"]

# --- 2. BARRA LATERAL: TIPO SLACK ---
with st.sidebar:
    st.header("⚙️ Sesión y Navegación")
    usuario_actual = st.selectbox("👤 Tu Usuario:", USUARIOS)
    
    st.divider()
    
    # Menú de navegación principal
    vista_seleccionada = st.radio(
        "📌 Sección:",
        ["📢 Canales", "✉️ Mensajes Directos", "🔔 Mi Actividad (@Menciones)"]
    )
    
    st.divider()
    
    # Subopciones según la vista
    canal_activo = None
    dm_destino = None
    
    if vista_seleccionada == "📢 Canales":
        canal_activo = st.selectbox("Selecciona Canal:", ["#general", "#mantenimiento", "#urgencias"])
    elif vista_seleccionada == "✉️ Mensajes Directos":
        destinatarios_posibles = [u for u in USUARIOS if u != usuario_actual]
        dm_destino = st.selectbox("Chat privado con:", destinatarios_posibles)

# --- 3. BASE DE DATOS EN MEMORIA (PRÓXIMAMENTE VINCULADA A GOOGLE SHEETS) ---
if "bd_chat" not in st.session_state:
    st.session_state.bd_chat = [
        {
            "ID_MENSAJE": "msg-1",
            "FECHA_HORA": "10:00 AM",
            "EMISOR": "Sistema",
            "MENSAJE": "Bienvenido al chat interno de la Dirección de Alumbrado Público.",
            "CANAL_DESTINO": "#general",
            "MENCIONADOS": "",
            "ID_PADRE": ""
        }
    ]

# Función para extraer menciones @usuario
def detectar_menciones(texto):
    menciones = re.findall(r'@\w+', texto)
    return ", ".join(menciones) if menciones else ""

# --- 4. RENDERIZADO DE MENSAJES SEGÚN LA VISTA ---

# --- OPCIÓN A: CANALES PÚBLICOS ---
if vista_seleccionada == "📢 Canales":
    st.subheader(f"Canal: `{canal_activo}`")
    
    # Filtrar solo mensajes principales del canal (sin hilos)
    mensajes_canal = [
        m for m in st.session_state.bd_chat 
        if m["CANAL_DESTINO"] == canal_activo and not m["ID_PADRE"]
    ]
    
    for msg in mensajes_canal:
        es_propio = (msg["EMISOR"] == usuario_actual)
        avatar = "👨‍💻" if "Admin" in msg["EMISOR"] else ("🤖" if msg["EMISOR"] == "Sistema" else "👷‍♂️")
        
        with st.chat_message("user" if es_propio else "assistant", avatar=avatar):
            st.markdown(f"**{msg['EMISOR']}** <small style='color:gray;'>({msg['FECHA_HORA']})</small>", unsafe_allow_html=True)
            st.write(msg["MENSAJE"])
            
            # --- HILOS (THREADS) ---
            hilos = [h for h in st.session_state.bd_chat if h["ID_PADRE"] == msg["ID_MENSAJE"]]
            cant_hilos = len(hilos)
            
            with st.expander(f"💬 {cant_hilos} respuestas en hilo" if cant_hilos > 0 else "💬 Responder en hilo"):
                for h in hilos:
                    st.markdown(f"↳ **{h['EMISOR']}**: {h['MENSAJE']} `<small style='color:gray;'>({h['FECHA_HORA']})</small>`", unsafe_allow_html=True)
                
                # Formulario para responder al hilo
                texto_hilo = st.text_input(f"Responder a {msg['EMISOR']}...", key=f"input_{msg['ID_MENSAJE']}")
                if st.button("Enviar respuesta", key=f"btn_{msg['ID_MENSAJE']}"):
                    if texto_hilo:
                        st.session_state.bd_chat.append({
                            "ID_MENSAJE": str(uuid.uuid4())[:8],
                            "FECHA_HORA": obtener_hora_mexico(),
                            "EMISOR": usuario_actual,
                            "MENSAJE": texto_hilo,
                            "CANAL_DESTINO": canal_activo,
                            "MENCIONADOS": detectar_menciones(texto_hilo),
                            "ID_PADRE": msg["ID_MENSAJE"]
                        })
                        st.rerun()

    # Entrada de mensaje principal en el canal
    nuevo_txt = st.chat_input(f"Enviar mensaje a {canal_activo}...")
    if nuevo_txt:
        st.session_state.bd_chat.append({
            "ID_MENSAJE": str(uuid.uuid4())[:8],
            "FECHA_HORA": obtener_hora_mexico(),
            "EMISOR": usuario_actual,
            "MENSAJE": nuevo_txt,
            "CANAL_DESTINO": canal_activo,
            "MENCIONADOS": detectar_menciones(nuevo_txt),
            "ID_PADRE": ""
        })
        st.rerun()

# --- OPCIÓN B: MENSAJES DIRECTOS (PRIVADOS) ---
elif vista_seleccionada == "✉️ Mensajes Directos":
    st.subheader(f"💬 Chat Privado con `{dm_destino}`")
    
    # Identificador único de la conversación entre 2 usuarios
    id_dm = "_".join(sorted([usuario_actual, dm_destino]))
    
    mensajes_dm = [m for m in st.session_state.bd_chat if m["CANAL_DESTINO"] == id_dm]
    
    for msg in mensajes_dm:
        es_propio = (msg["EMISOR"] == usuario_actual)
        with st.chat_message("user" if es_propio else "assistant"):
            st.markdown(f"**{msg['EMISOR']}** <small style='color:gray;'>({msg['FECHA_HORA']})</small>", unsafe_allow_html=True)
            st.write(msg["MENSAJE"])
            
    txt_dm = st.chat_input(f"Escribir a {dm_destino}...")
    if txt_dm:
        st.session_state.bd_chat.append({
            "ID_MENSAJE": str(uuid.uuid4())[:8],
            "FECHA_HORA": obtener_hora_mexico(),
            "EMISOR": usuario_actual,
            "MENSAJE": txt_dm,
            "CANAL_DESTINO": id_dm,
            "MENCIONADOS": "",
            "ID_PADRE": ""
        })
        st.rerun()

# --- OPCIÓN C: ACTIVIDAD (@MENCIONES) ---
elif vista_seleccionada == "🔔 Mi Actividad (@Menciones)":
    st.subheader(f"🔔 Menciones dirigidas a `{usuario_actual}`")
    
    # Búsqueda de menciones (ej. @Fermín)
    nombre_clave = usuario_actual.split()[0] # Toma "Fermín"
    menciones = [
        m for m in st.session_state.bd_chat 
        if f"@{nombre_clave}".lower() in m["MENSAJE"].lower()
    ]
    
    if not menciones:
        st.info("No tienes menciones recientes.")
    else:
        for msg in menciones:
            st.warning(f"**{msg['EMISOR']}** en `{msg['CANAL_DESTINO']}` ({msg['FECHA_HORA']}):\n\n{msg['MENSAJE']}")
