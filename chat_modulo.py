import streamlit as st
from supabase import create_client, Client
from datetime import datetime
from zoneinfo import ZoneInfo
import time

# 1. Conexión Segura a Supabase
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"🔴 Error al cargar las credenciales de Supabase en Secrets: {e}")
        st.stop()

# Helper para subir archivos al Bucket de Supabase Storage
def subir_adjunto_supabase(uploaded_file, supabase_client) -> str:
    """
    Suba un archivo cargado mediante st.file_uploader al bucket 'chat-adjuntos'
    y retorna la URL pública del archivo.
    """
    try:
        timestamp = int(time.time())
        nombre_archivo_limpio = uploaded_file.name.replace(" ", "_")
        path_destino = f"mensajes/{timestamp}_{nombre_archivo_limpio}"

        file_bytes = uploaded_file.getvalue()

        supabase_client.storage.from_("chat-adjuntos").upload(
            path=path_destino,
            file=file_bytes,
            file_options={"content-type": uploaded_file.type}
        )

        public_url = supabase_client.storage.from_("chat-adjuntos").get_public_url(path_destino)
        return public_url
    except Exception as e:
        st.error(f"🔴 Error al subir el archivo adjunto: {e}")
        return None

def render_chat():
    """
    Módulo de Chat aislado e independiente para SF Pangea.
    Migrado a Supabase con control de zona horaria (México), soporte de adjuntos y seguridad RLS.
    """
    st.header("💬 SF Pangea Chat")
    st.caption("Módulo de comunicación interna seguro y optimizado con Supabase")

    supabase = get_supabase_client()

    # 2. Control de Identificación de Usuario
    if "sf_chat_user" not in st.session_state:
        st.session_state.sf_chat_user = ""

    if not st.session_state.sf_chat_user:
        st.info("👋 Ingresa tu nombre o alias para ingresar al chat.")
        with st.form("form_registro_chat"):
            nombre_input = st.text_input("Nombre / Usuario:")
            btn_entrar = st.form_submit_button("Ingresar al Chat 🚀")
            if btn_entrar:
                if nombre_input.strip():
                    st.session_state.sf_chat_user = nombre_input.strip()
                    st.rerun()
                else:
                    st.warning("El nombre de usuario no puede estar vacío.")
        return

    # Barra superior de estado de sesión
    col_status, col_logout = st.columns([4, 1])
    with col_status:
        st.success(f"🟢 Usuario activo: **{st.session_state.sf_chat_user}**")
    with col_logout:
        if st.button("Cambiar usuario", key="sf_chat_btn_logout"):
            st.session_state.sf_chat_user = ""
            st.rerun()

    st.divider()

    # 3. Consulta de Historial en Supabase
    def cargar_historial(canal="general"):
        try:
            res = (
                supabase.table("mensajes")
                .select("*")
                .eq("canal", canal)
                .order("created_at", desc=False)
                .execute()
            )
            return res.data if res.data else []
        except Exception as err:
            st.error(f"🔴 Error al consultar mensajes en Supabase: {err}")
            return []

    # 4. Carga y Renderizado del Historial
    mensajes = cargar_historial(canal="general")

    chat_container = st.container()
    with chat_container:
        if mensajes:
            for fila in mensajes:
                usr = fila.get("emisor", "Anónimo")
                msg = fila.get("mensaje", "")
                url_adjunto = fila.get("url_adjunto", None)
                
                # Formatear fecha y hora convertida a Horario de México (UTC-6)
                raw_time = fila.get("created_at", "")
                if raw_time:
                    try:
                        dt_utc = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                        dt_local = dt_utc.astimezone(ZoneInfo("America/Mexico_City"))
                        tstamp = dt_local.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        tstamp = str(raw_time)
                else:
                    tstamp = ""

                es_propio = (usr == st.session_state.sf_chat_user)
                avatar_icon = "👤" if es_propio else "💬"

                with st.chat_message(usr, avatar=avatar_icon):
                    st.markdown(f"**{usr}** `<{tstamp}>`\n\n{msg}")
                    
                    # Renderizado del archivo adjunto (si existe en el registro)
                    if url_adjunto:
                        ext = url_adjunto.split("?")[0].split(".")[-1].lower()
                        if ext in ["png", "jpg", "jpeg", "webp", "gif"]:
                            st.image(url_adjunto, use_container_width=True)
                        else:
                            st.markdown(f"📎 **Adjunto:** [{url_adjunto.split('/')[-1]}]({url_adjunto})")
        else:
            st.info("No hay mensajes aún. ¡Sé el primero en escribir!")

    # 5. Entrada y Envío de Nuevos Mensajes con Adjuntos
    with st.popover("📎 Adjuntar evidencia o documento"):
        archivo_adjunto = st.file_uploader(
            "Selecciona una imagen o archivo",
            type=["png", "jpg", "jpeg", "pdf", "xlsx", "docx"],
            key="sf_chat_file_uploader"
        )
        if archivo_adjunto:
            st.caption(f"📄 Archivo listo: **{archivo_adjunto.name}**")

    prompt = st.chat_input("Escribe un mensaje para SF Pangea...")

    if prompt:
        url_adj = None
        
        # Procesar subida a Supabase Storage si se adjuntó archivo
        if archivo_adjunto is not None:
            with st.spinner("Subiendo archivo a Supabase Storage..."):
                url_adj = subir_adjunto_supabase(archivo_adjunto, supabase)

        nuevo_registro = {
            "canal": "general",
            "emisor": st.session_state.sf_chat_user,
            "mensaje": prompt,
            "destinatario": None,
            "url_adjunto": url_adj
        }

        try:
            supabase.table("mensajes").insert(nuevo_registro).execute()
            st.rerun()
        except Exception as write_err:
            st.error(f"🔴 Error al enviar mensaje: {write_err}")
