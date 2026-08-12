import re
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client

# Lista Oficial de Respaldo (27 Usuarios)
USUARIOS_OFICIALES_DEFAULT = [
    "SF_FERMIN", "Director", "Jefe Mant.", "Jefe Infra.", "Guadarrama",
    "Almacén1", "Almacén 2", "DAP1", "DAP2", "DAP3",
    "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10",
    "B11", "B12", "B13", "B14", "B15", "B16", "B17"
]

# 1. Conexión Segura a Supabase
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"🔴 Error al cargar credenciales de Supabase: {e}")
        st.stop()


# Sanitización estricta de nombres de archivos
def sanitizar_nombre_archivo(nombre_original: str) -> str:
    partes = nombre_original.rsplit(".", 1)
    nombre_base = partes[0]
    ext = partes[1] if len(partes) > 1 else ""

    nombre_base_limpio = re.sub(r"[^a-zA-Z0-9_-]", "_", nombre_base)
    ext_limpia = re.sub(r"[^a-zA-Z0-9]", "", ext)

    if ext_limpia:
        return f"{nombre_base_limpio}.{ext_limpia}"
    return nombre_base_limpio


# Subir archivo adjunto a Supabase Storage
def subir_adjunto_supabase(uploaded_file, supabase_client) -> str:
    try:
        timestamp = int(time.time() * 1000)
        nombre_limpio = sanitizar_nombre_archivo(uploaded_file.name)
        path_destino = f"mensajes/{timestamp}_{nombre_limpio}"

        file_bytes = uploaded_file.getvalue()

        supabase_client.storage.from_("chat-adjuntos").upload(
            path=path_destino,
            file=file_bytes,
            file_options={"content-type": uploaded_file.type},
        )

        public_url = supabase_client.storage.from_("chat-adjuntos").get_public_url(
            path_destino
        )
        return public_url
    except Exception as e:
        st.error(f"🔴 Error al subir el archivo {uploaded_file.name}: {e}")
        return None


# Descargar bytes con caché
@st.cache_data(ttl=3600, show_spinner=False)
def obtener_bytes_adjunto(url: str) -> bytes:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception:
        return None


# Consultar canales dinámicos
def obtener_canales_db(supabase_client) -> list:
    canales_predeterminados = [
        "general",
        "mantenimiento",
        "infraestructura",
        "dap",
        "mapas",
        "almacen",
    ]
    try:
        res = supabase_client.table("canales").select("nombre").execute()
        if res.data:
            canales_db = [
                row["nombre"].lower()
                for row in res.data
                if row.get("nombre")
            ]
            return sorted(list(set(canales_predeterminados + canales_db)))
    except Exception:
        pass
    return canales_predeterminados


# Consultar usuarios oficialmente registrados en la tabla 'usuarios'
def obtener_usuarios_registrados(supabase_client) -> list:
    try:
        res = (
            supabase_client.table("usuarios")
            .select("nombre")
            .order("nombre")
            .execute()
        )
        if res.data and len(res.data) > 0:
            db_users = [u["nombre"] for u in res.data if u.get("nombre")]
            return sorted(list(set(db_users + USUARIOS_OFICIALES_DEFAULT)))
    except Exception:
        pass
    return USUARIOS_OFICIALES_DEFAULT


# Motor de Menciones Inteligentes (Insensible a Mayúsculas/Minúsculas y Coincidencia por Prefijo)
def evaluar_mencion_inteligente(mensaje: str, usuario_destinatario: str) -> bool:
    if not mensaje or not usuario_destinatario:
        return False
    target_clean = usuario_destinatario.lower().replace(" ", "").replace(".", "")
    palabras = mensaje.lower().split()

    for palabra in palabras:
        if palabra.startswith("@"):
            tag = palabra[1:].strip(",.!?:;\"'")
            if len(tag) >= 2:
                tag_clean = tag.replace(" ", "").replace(".", "")
                if target_clean.startswith(tag_clean) or tag_clean in target_clean:
                    return True
    return False


# -----------------------------------------------------------------------------
# HISTORIAL DE MENSAJES AUTO-SINCRONIZADO
# -----------------------------------------------------------------------------
@st.fragment(run_every=2)
def render_historial_fragment(
    usuario_actual: str,
    canal: str = "general",
    destinatario: str = None,
    solo_menciones: bool = False,
    fecha_filtro=None,
    hora_inicio=None,
    hora_fin=None,
    texto_busqueda: str = "",
):
    supabase = get_supabase_client()

    if "notified_msg_ids" not in st.session_state:
        st.session_state.notified_msg_ids = set()

    def cargar_historial():
        try:
            query = supabase.table("mensajes").select("*")

            if solo_menciones:
                res = query.order("created_at", desc=True).execute()
                data = res.data if res.data else []
                data = [
                    m
                    for m in data
                    if evaluar_mencion_inteligente(m.get("mensaje", ""), usuario_actual)
                    and m.get("emisor") != usuario_actual
                ]
            elif canal == "privado" and destinatario:
                res = (
                    query.eq("canal", "privado")
                    .order("created_at", desc=False)
                    .execute()
                )
                data = res.data if res.data else []
                data = [
                    m
                    for m in data
                    if (
                        m.get("emisor") == usuario_actual
                        and m.get("destinatario") == destinatario
                    )
                    or (
                        m.get("emisor") == destinatario
                        and m.get("destinatario") == usuario_actual
                    )
                ]
            else:
                res = (
                    query.eq("canal", canal)
                    .order("created_at", desc=False)
                    .execute()
                )
                data = res.data if res.data else []

            if texto_busqueda and data:
                kw = texto_busqueda.strip().lower()
                data = [m for m in data if kw in m.get("mensaje", "").lower()]

            if fecha_filtro and data:
                data_filtrada = []
                for m in data:
                    raw_time = m.get("created_at", "")
                    if raw_time:
                        try:
                            dt_utc = datetime.fromisoformat(
                                raw_time.replace("Z", "+00:00")
                            )
                            dt_local = dt_utc.astimezone(
                                ZoneInfo("America/Mexico_City")
                            )

                            if dt_local.date() == fecha_filtro:
                                if hora_inicio and hora_fin:
                                    if (
                                        hora_inicio
                                        <= dt_local.time()
                                        <= hora_fin
                                    ):
                                        data_filtrada.append(m)
                                else:
                                    data_filtrada.append(m)
                        except Exception:
                            pass
                return data_filtrada

            return data
        except Exception as err:
            st.error(f"🔴 Error al consultar mensajes: {err}")
            return []

    mime_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "ppt": "application/vnd.ms-powerpoint",
    }

    hora_actual = datetime.now(ZoneInfo("America/Mexico_City")).strftime(
        "%H:%M:%S"
    )
    if solo_menciones:
        st.caption(
            f"🔔 **Muro de Menciones para @{usuario_actual}** • En vivo (`{hora_actual}`)"
        )
    elif canal == "privado":
        st.caption(
            f"🔒 **Chat Privado con {destinatario}** • En vivo (`{hora_actual}`)"
        )
    else:
        st.caption(
            f"📢 **Canal #{canal.upper()}** • Sincronizado en Vivo (`{hora_actual}`)"
        )

    mensajes = cargar_historial()

    chat_container = st.container(height=480)
    with chat_container:
        if mensajes:
            for msg_idx, fila in enumerate(mensajes):
                usr = fila.get("emisor", "Anónimo")
                msg = fila.get("mensaje", "")
                url_adjunto_raw = fila.get("url_adjunto", None)
                canal_origen = fila.get("canal", "general")
                msg_unique_id = (
                    fila.get("id") or f"{usr}_{fila.get('created_at', '')}"
                )

                raw_time = fila.get("created_at", "")
                if raw_time:
                    try:
                        dt_utc = datetime.fromisoformat(
                            raw_time.replace("Z", "+00:00")
                        )
                        dt_local = dt_utc.astimezone(
                            ZoneInfo("America/Mexico_City")
                        )
                        tstamp = dt_local.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        tstamp = str(raw_time)
                else:
                    tstamp = ""

                es_propio = usr == usuario_actual
                avatar_icon = "👤" if es_propio else "💬"

                contiene_mencion = (
                    evaluar_mencion_inteligente(msg, usuario_actual) and not es_propio
                )

                if (
                    contiene_mencion
                    and msg_unique_id not in st.session_state.notified_msg_ids
                ):
                    st.session_state.notified_msg_ids.add(msg_unique_id)
                    st.toast(
                        f"🔔 ¡{usr} te ha mencionado en #{canal_origen.upper()}!",
                        icon="💬",
                    )
                    components.html(
                        f"""
                        <audio autoplay style="display:none;">
                            <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg">
                        </audio>
                        <script>
                        if (Notification.permission === 'granted') {{
                            new Notification("🔔 SF Pangea Chat", {{
                                body: "{usr} te ha mencionado en #{canal_origen.upper()}",
                                icon: "https://cdn-icons-png.flaticon.com/512/732/732200.png"
                            }});
                        }} else if (Notification.permission !== 'denied') {{
                            Notification.requestPermission();
                        }}
                        </script>
                        """,
                        height=0,
                        width=0,
                    )

                with st.chat_message(usr, avatar=avatar_icon):
                    if contiene_mencion and not solo_menciones:
                        st.warning(
                            f"🔔 **¡{usr} te ha mencionado en este mensaje!**"
                        )

                    if solo_menciones:
                        st.info(
                            f"📌 Mencionado en canal: **#{canal_origen.upper()}**"
                        )

                    st.markdown(f"**{usr}** `<{tstamp}>`\n\n{msg}")

                    if url_adjunto_raw:
                        lista_urls = url_adjunto_raw.split("|")

                        for file_idx, url_adjunto in enumerate(lista_urls):
                            ext = (
                                url_adjunto.split("?")[0]
                                .split(".")[-1]
                                .lower()
                            )
                            nombre_archivo = (
                                url_adjunto.split("?")[0].split("/")[-1]
                            )
                            mime_actual = mime_types.get(
                                ext, "application/octet-stream"
                            )

                            st.markdown("---")
                            if ext in ["png", "jpg", "jpeg", "webp", "gif"]:
                                col_thumb, col_actions = st.columns([1, 2])

                                with col_thumb:
                                    st.image(url_adjunto, width=180)

                                with col_actions:
                                    st.link_button(
                                        "🌐 Abrir en pestaña",
                                        url_adjunto,
                                        use_container_width=True,
                                    )
                                    with st.expander(
                                        "🔍 Descargar / Vista previa"
                                    ):
                                        file_bytes = obtener_bytes_adjunto(
                                            url_adjunto
                                        )
                                        if file_bytes:
                                            st.download_button(
                                                label="📥 Descargar al equipo",
                                                data=file_bytes,
                                                file_name=nombre_archivo,
                                                mime=mime_actual,
                                                use_container_width=True,
                                                key=f"dl_btn_{msg_idx}_{file_idx}_{canal}",
                                            )
                                        st.image(
                                            url_adjunto,
                                            use_container_width=True,
                                        )
                            else:
                                icon_doc = "📄"
                                if ext in ["xlsx", "xls"]:
                                    icon_doc = "📊"
                                elif ext in ["docx", "doc"]:
                                    icon_doc = "📝"
                                elif ext in ["pptx", "ppt"]:
                                    icon_doc = "🖥️"
                                elif ext == "pdf":
                                    icon_doc = "📕"

                                st.markdown(
                                    f"{icon_doc} **Archivo adjunto:** `{nombre_archivo}`"
                                )
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    file_bytes = obtener_bytes_adjunto(
                                        url_adjunto
                                    )
                                    if file_bytes:
                                        st.download_button(
                                            label="📥 Descargar archivo",
                                            data=file_bytes,
                                            file_name=nombre_archivo,
                                            mime=mime_actual,
                                            use_container_width=True,
                                            key=f"dl_btn_file_{msg_idx}_{file_idx}_{canal}",
                                        )
                                with col_btn2:
                                    st.link_button(
                                        "🌐 Abrir en pestaña",
                                        url_adjunto,
                                        use_container_width=True,
                                    )
        else:
            st.info("No se encontraron mensajes.")


# -----------------------------------------------------------------------------
# REPOSITORIO DE ARCHIVOS PÚBLICOS (SÓLO CANALES PÚBLICOS)
# -----------------------------------------------------------------------------
def render_panel_archivos_publicos(supabase_client):
    st.subheader("📁 Repositorio de Archivos Públicos")
    st.caption(
        "Archivos compartidos en los canales de trabajo (Excluye chats 1 a 1)."
    )

    try:
        res = (
            supabase_client.table("mensajes")
            .select("*")
            .neq("canal", "privado")
            .not_.is_("url_adjunto", "null")
            .order("created_at", desc=True)
            .execute()
        )
        data = res.data if res.data else []
    except Exception as e:
        st.error(f"🔴 Error al cargar repositorio público: {e}")
        return

    if not data:
        st.info("📂 No hay archivos públicos en los canales de trabajo.")
        return

    archivos_lista = []
    for m in data:
        urls = m.get("url_adjunto", "").split("|")
        for u in urls:
            if u.strip():
                ext = u.split("?")[0].split(".")[-1].lower()
                nombre = u.split("?")[0].split("/")[-1]
                archivos_lista.append({
                    "nombre": nombre,
                    "url": u,
                    "extension": ext,
                    "emisor": m.get("emisor", "Anónimo"),
                    "canal": m.get("canal", "general"),
                    "mensaje": m.get("mensaje", ""),
                    "created_at": m.get("created_at", ""),
                })

    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
    with col_f1:
        kw_file = st.text_input(
            "🔍 Buscar nombre / folio:", placeholder="Ej. AIRIS-1234"
        )
    with col_f2:
        canales_disponibles = ["Todos"] + sorted(
            list({a["canal"].upper() for a in archivos_lista})
        )
        canal_filtro = st.selectbox(
            "Filtrar por Canal:", canales_disponibles
        )
    with col_f3:
        tipo_filtro = st.selectbox("Tipo de Archivo:", [
            "Todos",
            "📷 Imágenes",
            "📕 PDFs",
            "📊 Excel",
            "📝 Word",
        ])

    filtrados = archivos_lista
    if kw_file.strip():
        kw = kw_file.strip().lower()
        filtrados = [
            a
            for a in filtrados
            if kw in a["nombre"].lower() or kw in a["mensaje"].lower()
        ]

    if canal_filtro != "Todos":
        filtrados = [
            a for a in filtrados if a["canal"].upper() == canal_filtro
        ]

    if tipo_filtro.startswith("📷"):
        filtrados = [
            a
            for a in filtrados
            if a["extension"] in ["png", "jpg", "jpeg", "webp", "gif"]
        ]
    elif tipo_filtro.startswith("📕"):
        filtrados = [a for a in filtrados if a["extension"] == "pdf"]
    elif tipo_filtro.startswith("📊"):
        filtrados = [
            a for a in filtrados if a["extension"] in ["xlsx", "xls"]
        ]
    elif tipo_filtro.startswith("📝"):
        filtrados = [
            a for a in filtrados if a["extension"] in ["docx", "doc"]
        ]

    st.markdown(f"**Archivos encontrados: `{len(filtrados)}`**")
    st.markdown("---")

    for idx, item in enumerate(filtrados):
        col_icon, col_det, col_acc = st.columns([1, 4, 2])
        ext = item["extension"]
        icon_str = (
            "📷"
            if ext in ["png", "jpg", "jpeg", "webp", "gif"]
            else "📕" if ext == "pdf" else "📊" if ext in ["xlsx", "xls"] else "📄"
        )

        with col_icon:
            st.markdown(f"### {icon_str}")
        with col_det:
            st.markdown(f"**{item['nombre']}**")
            st.caption(
                f"👤 Por: **{item['emisor']}** | Canal: **#{item['canal'].upper()}**"
            )
        with col_acc:
            st.link_button(
                "🌐 Abrir", item["url"], use_container_width=True
            )
            bytes_f = obtener_bytes_adjunto(item["url"])
            if bytes_f:
                st.download_button(
                    label="📥 Descargar",
                    data=bytes_f,
                    file_name=item["nombre"],
                    key=f"repo_pub_dl_{idx}",
                    use_container_width=True,
                )
        st.markdown("---")


# -----------------------------------------------------------------------------
# REPOSITORIO DE ARCHIVOS PRIVADOS (SÓLO PRIVADOS DEL USUARIO ACTIVO)
# -----------------------------------------------------------------------------
def render_panel_archivos_privados(supabase_client, usuario_actual: str):
    st.subheader("🔒 Mis Archivos Privados")
    st.caption(
        "Archivos compartidos exclusivamente en tus chats 1 a 1."
    )

    try:
        res = (
            supabase_client.table("mensajes")
            .select("*")
            .eq("canal", "privado")
            .not_.is_("url_adjunto", "null")
            .order("created_at", desc=True)
            .execute()
        )
        data = res.data if res.data else []
    except Exception as e:
        st.error(f"🔴 Error al cargar repositorio privado: {e}")
        return

    data_user = [
        m
        for m in data
        if m.get("emisor") == usuario_actual
        or m.get("destinatario") == usuario_actual
    ]

    if not data_user:
        st.info("🔒 No tienes archivos recibidos o enviados en chats 1 a 1.")
        return

    archivos_lista = []
    for m in data_user:
        urls = m.get("url_adjunto", "").split("|")
        otro_usr = (
            m.get("destinatario")
            if m.get("emisor") == usuario_actual
            else m.get("emisor")
        )
        for u in urls:
            if u.strip():
                ext = u.split("?")[0].split(".")[-1].lower()
                nombre = u.split("?")[0].split("/")[-1]
                archivos_lista.append({
                    "nombre": nombre,
                    "url": u,
                    "extension": ext,
                    "emisor": m.get("emisor"),
                    "contacto": otro_usr,
                    "mensaje": m.get("mensaje", ""),
                })

    kw_priv_file = st.text_input(
        "🔍 Buscar en mis archivos privados:",
        placeholder="Nombre o palabra clave...",
    )
    filtrados = archivos_lista
    if kw_priv_file.strip():
        kw = kw_priv_file.strip().lower()
        filtrados = [
            a
            for a in filtrados
            if kw in a["nombre"].lower() or kw in a["mensaje"].lower()
        ]

    st.markdown(
        f"**Archivos privados de {usuario_actual}: `{len(filtrados)}`**"
    )
    st.markdown("---")

    for idx, item in enumerate(filtrados):
        col_icon, col_det, col_acc = st.columns([1, 4, 2])
        with col_icon:
            st.markdown("### 🔒")
        with col_det:
            st.markdown(f"**{item['nombre']}**")
            st.caption(
                f"De: **{item['emisor']}** | Para/Con: **{item['contacto']}**"
            )
        with col_acc:
            st.link_button(
                "🌐 Abrir", item["url"], use_container_width=True
            )
            bytes_f = obtener_bytes_adjunto(item["url"])
            if bytes_f:
                st.download_button(
                    label="📥 Descargar",
                    data=bytes_f,
                    file_name=item["nombre"],
                    key=f"repo_priv_dl_{idx}",
                    use_container_width=True,
                )
        st.markdown("---")


# -----------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL DEL MÓDULO
# -----------------------------------------------------------------------------
def render_chat():
    st.header("💬 SF Pangea Chat - Centro de Comunicación DAP")

    supabase = get_supabase_client()

    # Sincronización automática con la sesión global de app.py
    if "usuario_nombre" in st.session_state and st.session_state.usuario_nombre:
        st.session_state.sf_chat_user = st.session_state.usuario_nombre
    elif "session_user" in st.query_params:
        st.session_state.sf_chat_user = st.query_params["session_user"]

    if "sf_chat_user" not in st.session_state:
        st.session_state.sf_chat_user = ""

    if "upload_counter" not in st.session_state:
        st.session_state.upload_counter = 0

    if "notified_msg_ids" not in st.session_state:
        st.session_state.notified_msg_ids = set()

    # Inicio de Sesión mediante Selección de Usuario Registrado
    usuarios_registrados = obtener_usuarios_registrados(supabase)

    if not st.session_state.sf_chat_user:
        st.info("👋 Selecciona tu usuario para ingresar al sistema.")
        with st.form("form_registro_chat"):
            usr_select = st.selectbox(
                "Usuario Oficial Autorizado:", usuarios_registrados
            )
            btn_entrar = st.form_submit_button("Ingresar al Chat 🚀")
            if btn_entrar:
                st.session_state.sf_chat_user = usr_select
                st.query_params["session_user"] = usr_select
                st.rerun()
        return

    # Evaluación insensible a mayúsculas/minúsculas para el rol de Admin
    es_admin = st.session_state.sf_chat_user.strip().upper() == "SF_FERMIN"

    col_status, col_logout = st.columns([4, 1])
    with col_status:
        role_label = (
            "👑 **ADMINISTRADOR**" if es_admin else "👤 **COLABORADOR**"
        )
        st.caption(
            f"🟢 Usuario: **{st.session_state.sf_chat_user}** ({role_label})"
        )
    with col_logout:
        if st.button("Salir / Cambiar", key="sf_chat_btn_logout"):
            st.session_state.sf_chat_user = ""
            if "session_user" in st.query_params:
                del st.query_params["session_user"]
            st.rerun()

    modos = [
        "📢 Canales Públicos",
        "🔒 Chat 1 a 1",
        "🔔 Mis Menciones",
        "📁 Archivos Públicos",
        "🔒 Mis Archivos Privados",
    ]
    if es_admin:
        modos.append("⚙️ Panel Admin")

    modo_chat = st.radio(
        "Navegación:",
        modos,
        horizontal=True,
        key="sf_chat_modo_principal",
        label_visibility="collapsed",
    )

    # --- MODO 1: CANALES PÚBLICOS ---
    if modo_chat == "📢 Canales Públicos":
        canales_disponibles = obtener_canales_db(supabase)
        canales_labels = [c.capitalize() for c in canales_disponibles]

        canal_seleccionado = st.radio(
            "Canal activo:",
            canales_labels,
            horizontal=True,
            key="sf_chat_radio_canal",
            label_visibility="collapsed",
        )
        canal_activo = canal_seleccionado.lower()

        col_search, col_filter, col_clear = st.columns([3, 1, 1])
        f_fecha_c, f_h_ini_c, f_h_fin_c = None, None, None

        with col_search:
            kw_canal = st.text_input(
                "Buscar",
                key="kw_canal",
                placeholder="🔍 Buscar palabra clave o folio...",
                label_visibility="collapsed",
            )
        with col_filter:
            with st.popover("📅 Filtros"):
                if st.checkbox("Activar filtro de fecha", key="chk_f_canales"):
                    f_fecha_c = st.date_input(
                        "Selecciona día:", key="date_canales"
                    )
                    if st.checkbox(
                        "Especificar rango de horas", key="chk_h_canales"
                    ):
                        f_h_ini_c = st.time_input(
                            "Desde:",
                            datetime.strptime("00:00", "%H:%M").time(),
                            key="h_ini_c",
                        )
                        f_h_fin_c = st.time_input(
                            "Hasta:",
                            datetime.strptime("23:59", "%H:%M").time(),
                            key="h_fin_c",
                        )

        with col_clear:
            if es_admin:
                with st.popover("🧹 Vaciar"):
                    st.warning(
                        f"Se eliminarán todos los mensajes del canal #{canal_activo.upper()}."
                    )
                    if st.checkbox("⚠️ Confirmar borrado", key="chk_del_c"):
                        if st.button("Eliminar Historial 🗑️", type="primary"):
                            supabase.table("mensajes").delete().eq(
                                "canal", canal_activo
                            ).execute()
                            st.success("Canal vaciado con éxito.")
                            st.rerun()

        render_historial_fragment(
            st.session_state.sf_chat_user,
            canal=canal_activo,
            fecha_filtro=f_fecha_c,
            hora_inicio=f_h_ini_c,
            hora_fin=f_h_fin_c,
            texto_busqueda=kw_canal,
        )

        count = st.session_state.upload_counter
        with st.popover("📎 Adjuntar evidencias a #" + canal_activo.upper()):
            archivos_adjuntos = st.file_uploader(
                "Selecciona archivos",
                type=[
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                    "gif",
                    "pdf",
                    "xlsx",
                    "xls",
                    "docx",
                    "doc",
                    "pptx",
                    "ppt",
                ],
                accept_multiple_files=True,
                key=f"sf_chat_uploader_canales_{count}",
            )
            if archivos_adjuntos:
                folio_input = st.text_input(
                    "Número de Folio / Ticket / AIRIS *",
                    key=f"sf_chat_folio_canales_{count}",
                    placeholder="Ej. AIRIS-12345",
                )
                comentario_adjunto = st.text_area(
                    "Comentario (Opcional):",
                    key=f"sf_chat_comentario_canales_{count}",
                )
                if st.button(
                    "Enviar Evidencias 🚀",
                    key=f"btn_enviar_canales_{count}",
                    use_container_width=True,
                ):
                    if not folio_input.strip():
                        st.error(
                            "⚠️ Debes ingresar el Folio / Ticket / AIRIS."
                        )
                    else:
                        urls = [
                            subir_adjunto_supabase(f, supabase)
                            for f in archivos_adjuntos
                            if f
                        ]
                        urls_validas = [u for u in urls if u]
                        if urls_validas:
                            msg_f = f"📌 **Folio / Ticket / AIRIS:** `{folio_input.strip()}`"
                            if comentario_adjunto.strip():
                                msg_f += f"\n\n{comentario_adjunto.strip()}"
                            supabase.table("mensajes").insert({
                                "canal": canal_activo,
                                "emisor": st.session_state.sf_chat_user,
                                "mensaje": msg_f,
                                "destinatario": None,
                                "url_adjunto": "|".join(urls_validas),
                            }).execute()
                            st.session_state.upload_counter += 1
                            st.rerun()

        prompt_canal = st.chat_input(
            f"Escribe un mensaje en #{canal_activo.upper()}..."
        )
        if prompt_canal:
            supabase.table("mensajes").insert({
                "canal": canal_activo,
                "emisor": st.session_state.sf_chat_user,
                "mensaje": prompt_canal,
                "destinatario": None,
                "url_adjunto": None,
            }).execute()
            st.rerun()

    # --- MODO 2: CHAT PRIVADO 1 A 1 ---
    elif modo_chat == "🔒 Chat 1 a 1":
        colegas = [
            u for u in usuarios_registrados if u != st.session_state.sf_chat_user
        ]
        if colegas:
            destinatario_activo = st.selectbox(
                "Colega:", colegas, key="sf_chat_select_privado"
            )

            col_search_p, col_filter_p, col_clear_p = st.columns([3, 1, 1])
            f_fecha_p, f_h_ini_p, f_h_fin_p = None, None, None

            with col_search_p:
                kw_priv = st.text_input(
                    "Buscar",
                    key="kw_priv",
                    placeholder="🔍 Buscar palabra clave...",
                    label_visibility="collapsed",
                )
            with col_filter_p:
                with st.popover("📅 Filtros"):
                    if st.checkbox("Activar filtro de fecha", key="chk_f_privado"):
                        f_fecha_p = st.date_input(
                            "Selecciona día:", key="date_privado"
                        )
                        if st.checkbox(
                            "Especificar rango de horas", key="chk_h_privado"
                        ):
                            f_h_ini_p = st.time_input(
                                "Desde:",
                                datetime.strptime("00:00", "%H:%M").time(),
                                key="h_ini_p",
                            )
                            f_h_fin_p = st.time_input(
                                "Hasta:",
                                datetime.strptime("23:59", "%H:%M").time(),
                                key="h_fin_p",
                            )

            with col_clear_p:
                if es_admin:
                    with st.popover("🧹 Vaciar"):
                        st.warning(
                            f"Borrar conversación privada entre tú y {destinatario_activo}."
                        )
                        if st.checkbox("⚠️ Confirmar borrado", key="chk_del_priv"):
                            if st.button("Eliminar Chat 🗑️", type="primary"):
                                supabase.table("mensajes").delete().eq(
                                    "canal", "privado"
                                ).or_(
                                    f"and(emisor.eq.{st.session_state.sf_chat_user},destinatario.eq.{destinatario_activo}),and(emisor.eq.{destinatario_activo},destinatario.eq.{st.session_state.sf_chat_user})"
                                ).execute()
                                st.success("Chat privado eliminado.")
                                st.rerun()

            render_historial_fragment(
                st.session_state.sf_chat_user,
                canal="privado",
                destinatario=destinatario_activo,
                fecha_filtro=f_fecha_p,
                hora_inicio=f_h_ini_p,
                hora_fin=f_h_fin_p,
                texto_busqueda=kw_priv,
            )

            count = st.session_state.upload_counter
            with st.popover(
                f"📎 Adjuntar archivo privado para {destinatario_activo}"
            ):
                archivos_privados = st.file_uploader(
                    "Selecciona archivos",
                    type=[
                        "png",
                        "jpg",
                        "jpeg",
                        "webp",
                        "gif",
                        "pdf",
                        "xlsx",
                        "xls",
                        "docx",
                        "doc",
                        "pptx",
                        "ppt",
                    ],
                    accept_multiple_files=True,
                    key=f"sf_chat_uploader_priv_{count}",
                )
                if archivos_privados:
                    folio_priv = st.text_input(
                        "Número de Folio / Ticket / AIRIS *",
                        key=f"sf_chat_folio_priv_{count}",
                    )
                    coment_priv = st.text_area(
                        "Comentario (Opcional):",
                        key=f"sf_chat_coment_priv_{count}",
                    )
                    if st.button(
                        "Enviar Evidencia Privada 🚀",
                        key=f"btn_enviar_priv_{count}",
                        use_container_width=True,
                    ):
                        if not folio_priv.strip():
                            st.error(
                                "⚠️ Debes ingresar el Folio / Ticket / AIRIS."
                            )
                        else:
                            urls = [
                                subir_adjunto_supabase(f, supabase)
                                for f in archivos_privados
                                if f
                            ]
                            urls_validas = [u for u in urls if u]
                            if urls_validas:
                                msg_f = f"📌 **Folio / Ticket / AIRIS:** `{folio_priv.strip()}`"
                                if coment_priv.strip():
                                    msg_f += f"\n\n{coment_priv.strip()}"
                                supabase.table("mensajes").insert({
                                    "canal": "privado",
                                    "emisor": st.session_state.sf_chat_user,
                                    "mensaje": msg_f,
                                    "destinatario": destinatario_activo,
                                    "url_adjunto": "|".join(urls_validas),
                                }).execute()
                                st.session_state.upload_counter += 1
                                st.rerun()

            prompt_privado = st.chat_input(
                f"Mensaje privado directo para {destinatario_activo}..."
            )
            if prompt_privado:
                supabase.table("mensajes").insert({
                    "canal": "privado",
                    "emisor": st.session_state.sf_chat_user,
                    "mensaje": prompt_privado,
                    "destinatario": destinatario_activo,
                    "url_adjunto": None,
                }).execute()
                st.rerun()
        else:
            st.info("💡 Aún no hay otros usuarios registrados para chatear.")

    # --- MODO 3: MIS MENCIONES ---
    elif modo_chat == "🔔 Mis Menciones":
        col_search_m, col_filter_m = st.columns([3, 1])
        f_fecha_m, f_h_ini_m, f_h_fin_m = None, None, None

        with col_search_m:
            kw_menc = st.text_input(
                "Buscar",
                key="kw_menc",
                placeholder="🔍 Buscar en mis menciones...",
                label_visibility="collapsed",
            )
        with col_filter_m:
            with st.popover("📅 Filtros"):
                if st.checkbox("Activar filtro de fecha", key="chk_f_menciones"):
                    f_fecha_m = st.date_input(
                        "Selecciona día:", key="date_menciones"
                    )
                    if st.checkbox(
                        "Especificar rango de horas", key="chk_h_menciones"
                    ):
                        f_h_ini_m = st.time_input(
                            "Desde:",
                            datetime.strptime("00:00", "%H:%M").time(),
                            key="h_ini_m",
                        )
                        f_h_fin_m = st.time_input(
                            "Hasta:",
                            datetime.strptime("23:59", "%H:%M").time(),
                            key="h_fin_m",
                        )

        render_historial_fragment(
            st.session_state.sf_chat_user,
            solo_menciones=True,
            fecha_filtro=f_fecha_m,
            hora_inicio=f_h_ini_m,
            hora_fin=f_h_fin_m,
            texto_busqueda=kw_menc,
        )

    # --- MODO 4: ARCHIVOS PÚBLICOS ---
    elif modo_chat == "📁 Archivos Públicos":
        render_panel_archivos_publicos(supabase)

    # --- MODO 5: ARCHIVOS PRIVADOS ---
    elif modo_chat == "🔒 Mis Archivos Privados":
        render_panel_archivos_privados(supabase, st.session_state.sf_chat_user)

    # --- MODO 6: PANEL ADMIN (SOLO SF_FERMIN) ---
    elif modo_chat == "⚙️ Panel Admin" and es_admin:
        st.subheader("⚙️ Panel de Administración Global")
        st.caption("Administra los usuarios autorizados, canales y borrado del sistema.")

        col_adm_u1, col_adm_u2 = st.columns(2)

        with col_adm_u1:
            st.markdown("### 👤 Alta de Usuarios")
            nuevo_usr = st.text_input("Nombre de usuario:", placeholder="Ej. Juan_Perez")
            if st.button("Registrar Usuario ➕", use_container_width=True):
                u_clean = nuevo_usr.strip()
                if u_clean:
                    try:
                        supabase.table("usuarios").insert({"nombre": u_clean, "rol": "colaborador"}).execute()
                        st.success(f"Usuario '{u_clean}' registrado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar usuario: {e}")
                else:
                    st.warning("Nombre de usuario no válido.")

        with col_adm_u2:
            st.markdown("### 🗑️ Baja de Usuarios")
            usr_borrar = st.selectbox(
                "Selecciona usuario a eliminar:",
                [u for u in usuarios_registrados if u.upper() != "SF_FERMIN"]
            )
            if st.button("Eliminar Usuario ❌", use_container_width=True):
                try:
                    supabase.table("usuarios").delete().eq("nombre", usr_borrar).execute()
                    st.success(f"Usuario '{usr_borrar}' eliminado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")

        st.markdown("---")
        col_adm_c1, col_adm_c2 = st.columns(2)

        with col_adm_c1:
            st.markdown("### ➕ Crear Canal")
            nuevo_canal = st.text_input("Nombre de canal:", placeholder="Ej. Electrica")
            if st.button("Crear Canal 🚀", use_container_width=True):
                c_clean = re.sub(r"[^a-zA-Z0-9_]", "", nuevo_canal.strip().lower())
                if c_clean:
                    try:
                        supabase.table("canales").insert({"nombre": c_clean}).execute()
                        st.success(f"Canal #{c_clean.upper()} creado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear canal: {e}")

        with col_adm_c2:
            st.markdown("### 🔥 Purgar Todo el Chat")
            if st.checkbox("⚠️ Confirmar borrado completo de la base de datos", key="chk_wipe_all"):
                if st.button("BORRAR TODOS LOS MENSAJES", type="primary", use_container_width=True):
                    try:
                        supabase.table("mensajes").delete().neq("id", 0).execute()
                        st.success("Toda la base de datos de mensajes ha sido vaciada.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al purgar: {e}")
