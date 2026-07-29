import streamlit as st
import datetime
import uuid
import re
from zoneinfo import ZoneInfo

st.set_page_config(page_title="💬 SF Pangea Chat - Sandbox", layout="wide")

st.title("💬 SF Pangea Chat")

TZ_MEX = ZoneInfo("America/Mexico_City")

def obtener_datos_tiempo():
    ahora = datetime.datetime.now(TZ_MEX)
    fecha_iso = ahora.strftime("%Y-%m-%d")
    fecha_disp = ahora.strftime("%d/%m/%Y")
    hora_disp = ahora.strftime("%I:%M %p")
    return fecha_iso, fecha_disp, hora_disp

# --- CLAVE MAESTRA DE ADMINISTRADOR ---
CLAVE_ADMIN = "1827"

# --- 1. LISTA BASE DE USUARIOS Y CANALES ---
LISTA_USUARIOS_INICIAL = [
    "FERMIN",
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
] + [f"Brigada Campo {i}" for i in range(1, 18)]

if "lista_usuarios" not in st.session_state:
    st.session_state.lista_usuarios = LISTA_USUARIOS_INICIAL
else:
    for u in LISTA_USUARIOS_INICIAL:
        if u not in st.session_state.lista_usuarios:
            st.session_state.lista_usuarios.append(u)

if "lista_canales" not in st.session_state:
    st.session_state.lista_canales = ["#general", "#mantenimiento", "#urgencias", "#bodega_reportes"]

# --- 2. ENLACES RÁPIDOS POR URL ---
params = st.query_params
usuario_url = params.get("user") or params.get("usuario")

if "usuario_actual" not in st.session_state:
    if usuario_url and usuario_url in st.session_state.lista_usuarios:
        st.session_state.usuario_actual = usuario_url
    else:
        st.session_state.usuario_actual = "FERMIN"

# --- 3. ESTADOS DE NAVEGACIÓN Y HISTORIAL ---
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

hoy_iso, hoy_disp, hoy_hora = obtener_datos_tiempo()

if "bd_chat" not in st.session_state:
    st.session_state.bd_chat = [
        {
            "ID_MENSAJE": "msg-init-1",
            "FECHA_ISO": hoy_iso,
            "FECHA_HORA": f"{hoy_disp} 10:00 AM",
            "EMISOR": "Brigada DAP",
            "MENSAJE": "Reporte inicial listo. Atención @FERMIN favor de validar.",
            "CANAL_DESTINO": "#general",
            "MENCIONADOS": "FERMIN",
            "ID_PADRE": ""
        }
    ]

# FUNCION INTELIGENTE DE DETECCIÓN DE MENCIONES (Tolerante a mayúsculas/minúsculas)
def detectar_menciones_inteligente(texto, lista_usuarios):
    etiquetas_encontradas = re.findall(r'@(\w+)', texto)
    mencionados = set()
    
    for etq in etiquetas_encontradas:
        etq_low = etq.lower()
        for u in lista_usuarios:
            primer_nombre = u.split()[0].lower()
            nombre_completo = u.lower().replace(" ", "")
            if etq_low == primer_nombre or etq_low == nombre_completo:
                mencionados.add(u)
                
    return ", ".join(list(mencionados))

# --- 4. BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Sesión")
    
    index_usr = st.session_state.lista_usuarios.index(st.session_state.usuario_actual) if st.session_state.usuario_actual in st.session_state.lista_usuarios else 0
    usuario_actual = st.selectbox("👤 Tu Usuario:", st.session_state.lista_usuarios, index=index_usr)
    st.session_state.usuario_actual = usuario_actual
    
    usr_encoded = usuario_actual.replace(" ", "%20")
    link_rapido = f"https://sf-pangea-chat-test.streamlit.app/?user={usr_encoded}"
    
    with st.expander("📱 Enlace rápido para Celular"):
        st.caption("Envía este link por WhatsApp al usuario para que entre sin escribir datos:")
        st.code(link_rapido, language="text")

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

    # --- 📅 FILTRO POR FECHA ---
    st.divider()
    st.subheader("📅 Filtro por Fecha")
    activar_filtro_fecha = st.checkbox("Filtrar por fecha específica", value=False)
    fecha_filtro_iso = None
    if activar_filtro_fecha:
        fecha_sel = st.date_input("Selecciona día:", datetime.date.today())
        fecha_filtro_iso = fecha_sel.strftime("%Y-%m-%d")

    # --- PANEL EXCLUSIVO DE ADMINISTRADOR (ÚNICAMENTE PARA 'FERMIN') ---
    if usuario_actual == "FERMIN":
        st.divider()
        with st.expander("🛠️ Panel Admin (FERMIN)"):
            st.caption("🔒 Control exclusivo del Administrador")
            
            tab_crear, tab_eliminar, tab_vaciar = st.tabs(["➕ Crear", "🗑️ Eliminar", "🔥 Vaciar Chat"])
            
            with tab_crear:
                st.markdown("**Crear nuevo canal:**")
                nuevo_canal_nombre = st.text_input("Nombre del canal:", placeholder="ej. #obra_especial", key="in_crear_canal")
                if st.button("➕ Crear Canal"):
                    if nuevo_canal_nombre:
                        fmt = nuevo_canal_nombre.lower().strip()
                        if not fmt.startswith("#"):
                            fmt = f"#{fmt}"
                        if fmt not in st.session_state.lista_canales:
                            st.session_state.lista_canales.append(fmt)
                            st.success(f"Canal {fmt} creado.")
                            st.rerun()
                
                st.divider()
                st.markdown("**Crear nuevo usuario:**")
                nuevo_usuario_nombre = st.text_input("Nombre usuario/brigada:", placeholder="ej. Brigada Campo 18", key="in_crear_usr")
                if st.button("➕ Agregar Usuario"):
                    if nuevo_usuario_nombre and nuevo_usuario_nombre not in st.session_state.lista_usuarios:
                        st.session_state.lista_usuarios.append(nuevo_usuario_nombre)
                        st.success(f"Usuario {nuevo_usuario_nombre} creado.")
                        st.rerun()

            with tab_eliminar:
                st.markdown("**Eliminar Canal:**")
                canales_borrables = [c for c in st.session_state.lista_canales if c != "#general"]
                
                if canales_borrables:
                    canal_a_borrar = st.selectbox("Selecciona canal a borrar:", canales_borrables)
                    confirm_canal = st.checkbox(f"⚠️ Confirmar borrar {canal_a_borrar}", key="chk_del_canal")
                    if st.button("🗑️ Eliminar Canal", disabled=not confirm_canal, type="primary"):
                        st.session_state.lista_canales.remove(canal_a_borrar)
                        if st.session_state.canal_activo == canal_a_borrar:
                            st.session_state.canal_activo = "#general"
                        st.success(f"Canal {canal_a_borrar} eliminado.")
                        st.rerun()
                else:
                    st.caption("No hay canales secundarios para borrar.")

                st.divider()
                st.markdown("**Eliminar Usuario:**")
                usuarios_borrables = [u for u in st.session_state.lista_usuarios if u != "FERMIN"]
                usr_a_borrar = st.selectbox("Selecciona usuario a borrar:", usuarios_borrables)
                confirm_usr = st.checkbox(f"⚠️ Confirmar borrar '{usr_a_borrar}'", key="chk_del_usr")
                
                if st.button("🗑️ Eliminar Usuario", disabled=not confirm_usr, type="primary"):
                    st.session_state.lista_usuarios.remove(usr_a_borrar)
                    st.success(f"Usuario '{usr_a_borrar}' eliminado.")
                    st.rerun()

            with tab_vaciar:
                st.markdown("**🔥 Vaciar todo el historial de mensajes:**")
                st.warning("Esta acción borrará TODOS los mensajes de todos los canales y chats directos.")
                
                clave_input = st.text_input("🔑 Clave de seguridad admin:", type="password", key="in_clave_del_all")
                confirm_vaciar = st.checkbox("⚠️ Entiendo las consecuencias y deseo borrar todo el historial", key="chk_del_all")
                
                if st.button("🔥 Vaciar Historial Completo", disabled=not confirm_vaciar, type="primary"):
                    if str(clave_input).strip() == str(CLAVE_ADMIN).strip():
                        st.session_state.bd_chat = []
                        st.session_state.menciones_leidas = set()
                        st.success("🧹 Historial de chat vaciado correctamente.")
                        st.rerun()
                    else:
                        st.error("❌ Clave de seguridad incorrecta. Acceso denegado.")

# --- 5. RENDERIZADO DE CONTENIDO PRINCIPAL ---

# A) CANALES
if st.session_state.seccion_activa == "📢 Canales":
    st.subheader(f"Canal: `{st.session_state.canal_activo}`")
    
    mensajes_canal = [
        m for m in st.session_state.bd_chat 
        if m["CANAL_DESTINO"] == st.session_state.canal_activo and not m["ID_PADRE"]
    ]
    
    if activar_filtro_fecha and fecha_filtro_iso:
        mensajes_canal = [m for m in mensajes_canal if m.get("FECHA_ISO") == fecha_filtro_iso]
        st.info(f"📅 Mostrando mensajes del día: `{fecha_sel.strftime('%d/%m/%Y')}`")

    if not mensajes_canal:
        st.info(f"No hay mensajes para mostrar en `{st.session_state.canal_activo}` con los filtros actuales.")
    else:
        for msg in mensajes_canal[-50:]:
            es_propio = (msg["EMISOR"] == usuario_actual)
            avatar = "👨‍💻" if msg["EMISOR"] == "FERMIN" else ("👔" if "Director" in msg["EMISOR"] or "Jefe" in msg["EMISOR"] else "👷‍♂️")
            
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
                            f_iso, f_disp, h_disp = obtener_datos_tiempo()
                            st.session_state.bd_chat.append({
                                "ID_MENSAJE": str(uuid.uuid4())[:8],
                                "FECHA_ISO": f_iso,
                                "FECHA_HORA": f"{f_disp} {h_disp}",
                                "EMISOR": usuario_actual,
                                "MENSAJE": texto_hilo,
                                "CANAL_DESTINO": st.session_state.canal_activo,
                                "MENCIONADOS": detectar_menciones_inteligente(texto_hilo, st.session_state.lista_usuarios),
                                "ID_PADRE": msg["ID_MENSAJE"]
                            })
                            st.rerun()

    nuevo_txt = st.chat_input(f"Enviar mensaje a {st.session_state.canal_activo}...")
    if nuevo_txt:
        f_iso, f_disp, h_disp = obtener_datos_tiempo()
        st.session_state.bd_chat.append({
            "ID_MENSAJE": str(uuid.uuid4())[:8],
            "FECHA_ISO": f_iso,
            "FECHA_HORA": f"{f_disp} {h_disp}",
            "EMISOR": usuario_actual,
            "MENSAJE": nuevo_txt,
            "CANAL_DESTINO": st.session_state.canal_activo,
            "MENCIONADOS": detectar_menciones_inteligente(nuevo_txt, st.session_state.lista_usuarios),
            "ID_PADRE": ""
        })
        st.rerun()

# B) MENSAJES DIRECTOS
elif st.session_state.seccion_activa == "✉️ Mensajes Directos":
    destinatarios = [u for u in st.session_state.lista_usuarios if u != usuario_actual]
    
    col_t, col_s = st.columns([1, 1])
    with col_t:
        st.subheader("✉️ Mensajes Directos")
    with col_s:
        dm_elegido = st.selectbox(
            "💬 Selecciona destinatario:",
            destinatarios,
            index=destinatarios.index(st.session_state.dm_activo) if st.session_state.dm_activo in destinatarios else 0
        )
        st.session_state.dm_activo = dm_elegido

    st.caption(f"🔒 Canal privado entre **{usuario_actual}** y **{st.session_state.dm_activo}**")
    st.divider()
    
    id_dm = "_".join(sorted([usuario_actual, st.session_state.dm_activo]))
    mensajes_dm = [m for m in st.session_state.bd_chat if m["CANAL_DESTINO"] == id_dm]
    
    if activar_filtro_fecha and fecha_filtro_iso:
        mensajes_dm = [m for m in mensajes_dm if m.get("FECHA_ISO") == fecha_filtro_iso]
        st.info(f"📅 Mostrando chats del día: `{fecha_sel.strftime('%d/%m/%Y')}`")
    
    if not mensajes_dm:
        st.info(f"No hay mensajes registrados con {st.session_state.dm_activo} para esta fecha.")
    else:
        for msg in mensajes_dm[-50:]:
            es_propio = (msg["EMISOR"] == usuario_actual)
            with st.chat_message("user" if es_propio else "assistant"):
                st.markdown(f"**{msg['EMISOR']}** <small style='color:gray;'>({msg['FECHA_HORA']})</small>", unsafe_allow_html=True)
                st.write(msg["MENSAJE"])
            
    txt_dm = st.chat_input(f"Escribir mensaje privado a {st.session_state.dm_activo}...")
    if txt_dm:
        f_iso, f_disp, h_disp = obtener_datos_tiempo()
        st.session_state.bd_chat.append({
            "ID_MENSAJE": str(uuid.uuid4())[:8],
            "FECHA_ISO": f_iso,
            "FECHA_HORA": f"{f_disp} {h_disp}",
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
    
    dict_mensajes = {m["ID_MENSAJE"]: m for m in st.session_state.bd_chat}
    menciones_y_respuestas = []
    
    for m in st.session_state.bd_chat:
        if m["EMISOR"] == usuario_actual:
            continue  # Ignorar mensajes propios
            
        es_mencionado = usuario_actual in m.get("MENCIONADOS", "")
        
        # Verificar si es respuesta a un mensaje del usuario actual
        es_respuesta_a_mi = False
        if m.get("ID_PADRE"):
            padre = dict_mensajes.get(m["ID_PADRE"])
            if padre and padre["EMISOR"] == usuario_actual:
                es_respuesta_a_mi = True
                
        if es_mencionado or es_respuesta_a_mi:
            # Marcamos el tipo de notificación
            tipo_notif = "mencion" if es_mencionado else "respuesta"
            m_copy = dict(m)
            m_copy["TIPO_NOTIF"] = tipo_notif
            menciones_y_respuestas.append(m_copy)

    if activar_filtro_fecha and fecha_filtro_iso:
        menciones_y_respuestas = [m for m in menciones_y_respuestas if m.get("FECHA_ISO") == fecha_filtro_iso]

    pendientes = [m for m in menciones_y_respuestas if m["ID_MENSAJE"] not in st.session_state.menciones_leidas]
    leidas = [m for m in menciones_y_respuestas if m["ID_MENSAJE"] in st.session_state.menciones_leidas]
    
    st.markdown("### 🔴 Pendientes (Prioridad)")
    if not pendientes:
        st.success("🎉 ¡Estás al día! No tienes menciones ni respuestas pendientes.")
    else:
        for msg in pendientes:
            with st.container(border=True):
                if msg.get("TIPO_NOTIF") == "respuesta":
                    st.markdown(f"💬 **{msg['EMISOR']}** respondió a tu mensaje en `{msg['CANAL_DESTINO']}` <small>({msg['FECHA_HORA']})</small>", unsafe_allow_html=True)
                else:
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
