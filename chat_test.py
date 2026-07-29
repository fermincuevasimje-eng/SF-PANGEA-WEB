import streamlit as st
import datetime
import uuid
import re
from zoneinfo import ZoneInfo

st.set_page_config(page_title="💬 SF Pangea Chat - Sandbox", layout="wide")

st.title("💬 SF Pangea Chat")

def obtener_hora_mexico():
    return datetime.datetime.now(ZoneInfo("America/Mexico_City")).strftime("%I:%M %p")

# --- 1. ESTRUCTURA INICIAL DE USUARIOS Y CANALES ---
LISTA_USUARIOS_INICIAL = [
    "Fermín (Admin)",
    "Director",
    "Jefe 1",
    "Jefe 2",
    "Especial 1",
    "Especial 2",
    "Bodega 1",
    "Bodega 2",
    "Brigada DAP",
    "Brigada Especial",
    "Brigada Mantenimiento Interno",
    "Cuadrilla Alumbrado"
] + [f"Brigada Campo {i}" for i in range(1, 18)] # Genera automáticamente Brigada Campo 1 a 17

if "lista_usuarios" not in st.session_state:
    st.session_state.lista_usuarios = LISTA_USUARIOS_INICIAL

if "lista_canales" not in st.session_state:
    st.session_state.lista_canales = ["#general", "#mantenimiento", "#urgencias", "#bodega_reportes"]

# --- 2. CONTROL DE NAVEGACIÓN Y MENSAJES ---
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "📢 Canales"

if "canal_activo" not in st.session_state:
    st.session_state.canal_activo = "#general"

if "dm_activo" not in st.session_state:
    st.session_state.dm_activo = "Director"

if "menciones_leidas" not in st.session_state:
    st.session_state.menciones_leidas = set()

if "mensaje_destacado" not in st.session_state:
    st.session_state.mensaje_destacado = None

if "bd_chat" not in st.session_state:
    st.session_state.bd_chat = [
        {
            "ID_MENSAJE": "msg-init-1",
            "FECHA_HORA": "10:00 AM",
            "EMISOR": "Brigada DAP",
            "MENSAJE": "Reporte inicial listo. Atención @Fermín favor de validar.",
            "CANAL_DESTINO": "#general",
            "MENCIONADOS": "@Fermín",
            "ID_PADRE": ""
        }
    ]

def detectar_menciones(texto):
    menciones = re.findall(r'@\w+', texto)
    return ", ".join(menciones) if menciones else ""

# --- 3. BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Sesión")
    usuario_actual = st.selectbox("👤 Tu Usuario:", st.session_state.lista_usuarios)
    
    st.divider()
    
    seccion = st.radio(
        "📌 Navegación:",
        ["📢 Canales", "✉️ Mensajes Directos", "🔔 Mi Actividad (@Menciones)"],
        index=["📢 Canales", "✉️ Mensajes Directos", "🔔 Mi Actividad (@Menciones)"].index(st.session_state.seccion_activa)
    )
    st.session_state.seccion_activa = seccion
    
    st.divider()
    
    if st.session_state.seccion_activa == "📢 Canales":
        canal_sel = st.selectbox(
            "Canal activo:", 
            st.session_state.lista_canales,
            index=st.session_state.lista_canales.index(st.session_state.canal_activo) if st.session_state.canal_activo in st.session_state.lista_canales else 0
        )
        st.session_state.canal_activo = canal_sel
        
    elif st.session_state.seccion_activa == "✉️ Mensajes Directos":
        destinatarios = [u for u in st.session_state.lista_usuarios if u != usuario_actual]
        dm_sel = st.selectbox(
            "Chat privado con:", 
            destinatarios,
            index=destinatarios.index(st.session_state.dm_activo) if st.session_state.dm_activo in destinatarios else 0
        )
        st.session_state.dm_activo = dm_sel

    # --- PANEL EXCLUSIVO DE ADMINISTRADOR ---
    if "Admin" in usuario_actual or usuario_actual == "Fermín":
        st.divider()
        with st.expander("🛠️ Panel de Administración"):
            st.caption("Solo visible para el Administrador")
            
            # Crear Nuevo Canal
            nuevo_canal_nombre = st.text_input("Nombre del nuevo canal:", placeholder="ej. #obra_especial")
            if st.button("➕ Crear Canal"):
                if nuevo_canal_nombre:
                    formateado = nuevo_canal_nombre.lower().strip()
                    if not formateado.startswith("#"):
                        formateado = f"#{formateado}"
                    if formateado not in st.session_state.lista_canales:
                        st.session_state.lista_canales.append(formateado)
                        st.success(f"Canal {formateado} creado.")
                        st.rerun()
            
            st.divider()
            
            # Crear Nuevo Usuario
            nuevo_usuario_nombre = st.text_input("Nombre de nuevo usuario/equipo:", placeholder="ej. Brigada Campo 18")
            if st.button("➕ Agregar Usuario"):
                if nuevo_usuario_nombre and nuevo_usuario_nombre not in st.session_state.lista_usuarios:
                    st.session_state.lista_usuarios.append(nuevo_usuario_nombre)
                    st.success(f"Usuario {nuevo_usuario_nombre} agregado.")
                    st.rerun()

# --- 4. RENDERIZADO DE CONTENIDO PRINCIPAL ---

# A) CANALES
if st.session_state.seccion_activa == "📢 Canales":
    st.subheader(f"Canal: `{st.session_state.canal_activo}`")
    
    # Optimización: Solo se renderizan los mensajes pertenecientes a este canal
    mensajes_canal = [
        m for m in st.session_state.bd_chat 
        if m["CANAL_DESTINO"] == st.session_state.canal_activo and not m["ID_PADRE"]
    ]
    
    # Límite de optimización de vista (mostrar últimos 50)
    for msg in mensajes_canal[-50:]:
        es_propio = (msg["EMISOR"] == usuario_actual)
        avatar = "👨‍💻" if "Admin" in msg["EMISOR"] else ("👔" if "Director" in msg["EMISOR"] or "Jefe" in msg["EMISOR"] else "👷‍♂️")
        
        es_destacado = (st.session_state.mensaje_destacado == msg["ID_MENSAJE"])
        if es_destacado:
            st.info("👇 **Mensaje seleccionado desde tus menciones:**")
            
        with st.chat_message("user" if es_propio else "assistant", avatar=avatar):
            st.markdown(f"**{msg['EMISOR']}** <small style='color:gray;'>({msg['FECHA_HORA']})</small>", unsafe_allow_html=True)
            st.write(msg["MENSAJE"])
            
            # Hilos
            hilos = [h for h in st.session_state.bd_chat if h["ID_PADRE"] == msg["ID_MENSAJE"]]
            cant_hilos = len(hilos)
            
            with st.expander(f"💬 {cant_hilos} respuestas en hilo" if cant_hilos > 0 else "💬 Responder en hilo"):
                for h in hilos:
                    st.markdown(f"↳ **{h['EMISOR']}**: {h['MENSAJE']} `<small style='color:gray;'>({h['FECHA_HORA']})</small>`", unsafe_allow_html=True)
                
                texto_hilo = st.text_input(f"Responder a {msg['EMISOR']}...", key=f"input_{msg['ID_MENSAJE']}")
                if st.button("Enviar respuesta", key=f"btn_{msg['ID_MENSAJE']}"):
                    if texto_hilo:
                        st.session_state.bd_chat.append({
                            "ID_MENSAJE": str(uuid.uuid4())[:8],
                            "FECHA_HORA": obtener_hora_mexico(),
                            "EMISOR": usuario_actual,
                            "MENSAJE": texto_hilo,
                            "CANAL_DESTINO": st.session_state.canal_activo,
                            "MENCIONADOS": detectar_menciones(texto_hilo),
                            "ID_PADRE": msg["ID_MENSAJE"]
                        })
                        st.rerun()

    nuevo_txt = st.chat_input(f"Enviar mensaje a {st.session_state.canal_activo}...")
    if nuevo_txt:
        st.session_state.bd_chat.append({
            "ID_MENSAJE": str(uuid.uuid4())[:8],
            "FECHA_HORA": obtener_hora_mexico(),
            "EMISOR": usuario_actual,
            "MENSAJE": nuevo_txt,
            "CANAL_DESTINO": st.session_state.canal_activo,
            "MENCIONADOS": detectar_menciones(nuevo_txt),
            "ID_PADRE": ""
        })
        st.rerun()

# B) MENSAJES DIRECTOS
elif st.session_state.seccion_activa == "✉️ Mensajes Directos":
    st.subheader(f"💬 Chat Privado con `{st.session_state.dm_activo}`")
    
    id_dm = "_".join(sorted([usuario_actual, st.session_state.dm_activo]))
    mensajes_dm = [m for m in st.session_state.bd_chat if m["CANAL_DESTINO"] == id_dm]
    
    for msg in mensajes_dm[-50:]:
        es_propio = (msg["EMISOR"] == usuario_actual)
        with st.chat_message("user" if es_propio else "assistant"):
            st.markdown(f"**{msg['EMISOR']}** <small style='color:gray;'>({msg['FECHA_HORA']})</small>", unsafe_allow_html=True)
            st.write(msg["MENSAJE"])
            
    txt_dm = st.chat_input(f"Escribir a {st.session_state.dm_activo}...")
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

# C) ACTIVIDAD
elif st.session_state.seccion_activa == "🔔 Mi Actividad (@Menciones)":
    st.subheader(f"🔔 Notificaciones para `{usuario_actual}`")
    
    nombre_clave = usuario_actual.split()[0]
    
    menciones = [
        m for m in st.session_state.bd_chat 
        if f"@{nombre_clave}".lower() in m["MENSAJE"].lower()
    ]
    
    pendientes = [m for m in menciones if m["ID_MENSAJE"] not in st.session_state.menciones_leidas]
    leidas = [m for m in menciones if m["ID_MENSAJE"] in st.session_state.menciones_leidas]
    
    st.markdown("### 🔴 Pendientes (Prioridad)")
    if not pendientes:
        st.success("🎉 ¡Estás al día! No tienes menciones pendientes.")
    else:
        for msg in pendientes:
            with st.container(border=True):
                st.markdown(f"🚨 **{msg['EMISOR']}** te etiquetó en `{msg['CANAL_DESTINO']}` <small>({msg['FECHA_HORA']})</small>", unsafe_allow_html=True)
                st.write(f"_{msg['MENSAJE']}_")
                
                if st.button("📍 Ir al mensaje", key=f"btn_ir_{msg['ID_MENSAJE']}"):
                    st.session_state.menciones_leidas.add(msg["ID_MENSAJE"])
                    if msg["CANAL_DESTINO"].startswith("#"):
                        st.session_state.seccion_activa = "📢 Canales"
                        st.session_state.canal_activo = msg["CANAL_DESTINO"]
                    st.session_state.mensaje_destacado = msg["ID_MENSAJE"]
                    st.rerun()

    if leidas:
        st.divider()
        st.markdown("### ⚪ Historial (Atendidas)")
        for msg in leidas:
            with st.container(border=True):
                st.markdown(f"✅ **{msg['EMISOR']}** en `{msg['CANAL_DESTINO']}` <small>({msg['FECHA_HORA']})</small>", unsafe_allow_html=True)
                st.write(f"_{msg['MENSAJE']}_")
                if st.button("👁️ Volver a ver", key=f"btn_ver_{msg['ID_MENSAJE']}"):
                    if msg["CANAL_DESTINO"].startswith("#"):
                        st.session_state.seccion_activa = "📢 Canales"
                        st.session_state.canal_activo = msg["CANAL_DESTINO"]
                    st.session_state.mensaje_destacado = msg["ID_MENSAJE"]
                    st.rerun()
