import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from supabase import Client, create_client


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


# Helper para subir un archivo individual al Bucket de Supabase Storage
def subir_adjunto_supabase(uploaded_file, supabase_client) -> str:
  try:
    timestamp = int(time.time() * 1000)
    nombre_archivo_limpio = uploaded_file.name.replace(" ", "_")
    path_destino = f"mensajes/{timestamp}_{nombre_archivo_limpio}"

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


# Helper en caché para descargar bytes y habilitar descarga nativa en celulares
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


# -----------------------------------------------------------------------------
# FASE 3: Fragmento aislado para Auto-Refresco en tiempo real (Sincronización fluida)
# -----------------------------------------------------------------------------
@st.fragment(run_every=5)
def render_historial_fragment(usuario_actual: str, canal: str = "general"):
  # Obtenemos la conexión aquí adentro para evitar bloqueos del fragmento
  supabase = get_supabase_client()

  def cargar_historial():
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

  mime_types = {
      "png": "image/png",
      "jpg": "image/jpeg",
      "jpeg": "image/jpeg",
      "webp": "image/webp",
      "gif": "image/gif",
      "pdf": "application/pdf",
      "xlsx": (
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
      "xls": "application/vnd.ms-excel",
      "docx": (
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      ),
      "doc": "application/msword",
      "pptx": (
          "application/vnd.openxmlformats-officedocument.presentationml.presentation"
      ),
      "ppt": "application/vnd.ms-powerpoint",
  }

  # Indicador visual del estado del auto-refresco
  hora_actual = datetime.now(ZoneInfo("America/Mexico_City")).strftime(
      "%H:%M:%S"
  )
  st.caption(
      f"🟢 **Chat Sincronizado en Vivo** • Última actualización: `{hora_actual}`"
  )

  mensajes = cargar_historial()

  chat_container = st.container()
  with chat_container:
    if mensajes:
      for msg_idx, fila in enumerate(mensajes):
        usr = fila.get("emisor", "Anónimo")
        msg = fila.get("mensaje", "")
        url_adjunto_raw = fila.get("url_adjunto", None)

        # Horario de México (UTC-6)
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

        es_propio = usr == usuario_actual
        avatar_icon = "👤" if es_propio else "💬"

        with st.chat_message(usr, avatar=avatar_icon):
          st.markdown(f"**{usr}** `<{tstamp}>`\n\n{msg}")

          if url_adjunto_raw:
            lista_urls = url_adjunto_raw.split("|")

            for file_idx, url_adjunto in enumerate(lista_urls):
              ext = url_adjunto.split("?")[0].split(".")[-1].lower()
              nombre_archivo = url_adjunto.split("?")[0].split("/")[-1]

              file_bytes = obtener_bytes_adjunto(url_adjunto)
              mime_actual = mime_types.get(ext, "application/octet-stream")

              st.markdown("---")
              if ext in ["png", "jpg", "jpeg", "webp", "gif"]:
                col_thumb, col_actions = st.columns([1, 2])

                with col_thumb:
                  st.image(url_adjunto, width=180)

                with col_actions:
                  if file_bytes:
                    st.download_button(
                        label="📥 Descargar al celular / PC",
                        data=file_bytes,
                        file_name=nombre_archivo,
                        mime=mime_actual,
                        use_container_width=True,
                        key=f"dl_btn_{msg_idx}_{file_idx}",
                    )
                  st.link_button(
                      "🌐 Abrir en pestaña",
                      url_adjunto,
                      use_container_width=True,
                  )
                  with st.expander("🔍 Vista previa en chat"):
                    st.image(url_adjunto, use_container_width=True)
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
                  if file_bytes:
                    st.download_button(
                        label="📥 Descargar archivo",
                        data=file_bytes,
                        file_name=nombre_archivo,
                        mime=mime_actual,
                        use_container_width=True,
                        key=f"dl_btn_file_{msg_idx}_{file_idx}",
                    )
                with col_btn2:
                  st.link_button(
                      "🌐 Abrir en pestaña",
                      url_adjunto,
                      use_container_width=True,
                  )
    else:
      st.info("No hay mensajes aún. ¡Sé el primero en escribir!")


# -----------------------------------------------------------------------------
# Función principal de Renderizado del Módulo
# -----------------------------------------------------------------------------
def render_chat():
  st.header("💬 SF Pangea Chat")
  st.caption("Módulo de comunicación interna seguro y optimizado con Supabase")

  supabase = get_supabase_client()

  # 2. Control de Identificación de Usuario
  if "sf_chat_user" not in st.session_state:
    st.session_state.sf_chat_user = ""

  if "upload_counter" not in st.session_state:
    st.session_state.upload_counter = 0

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

  # Llama al fragmento pasando solo tipos de datos simples (String)
  render_historial_fragment(st.session_state.sf_chat_user, canal="general")

  # 5. Entrada para Adjuntar Archivos
  count = st.session_state.upload_counter
  with st.popover("📎 Adjuntar evidencias o documentos"):
    archivos_adjuntos = st.file_uploader(
        "Selecciona uno o varios archivos",
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
        key=f"sf_chat_uploader_{count}",
    )

    if archivos_adjuntos:
      st.caption(f"📁 **Archivos seleccionados:** {len(archivos_adjuntos)}")

      folio_input = st.text_input(
          "Número de Folio / Ticket / AIRIS *",
          key=f"sf_chat_folio_{count}",
          placeholder="Ej. AIRIS-12345 / Folio 987",
      )
      comentario_adjunto = st.text_area(
          "Comentario adicional (Opcional):",
          key=f"sf_chat_comentario_{count}",
          placeholder="Detalles sobre las evidencias...",
      )

      if st.button(
          "Enviar Evidencias 🚀",
          key=f"btn_enviar_{count}",
          use_container_width=True,
      ):
        if not folio_input.strip():
          st.error(
              "⚠️ Debes ingresar obligatoriamente el número de Folio / Ticket /"
              " AIRIS."
          )
        else:
          urls_subidas = []
          with st.spinner("Subiendo archivos a Supabase Storage..."):
            for f in archivos_adjuntos:
              url_f = subir_adjunto_supabase(f, supabase)
              if url_f:
                urls_subidas.append(url_f)

          if urls_subidas:
            url_adjunto_final = "|".join(urls_subidas)

            mensaje_final = (
                f"📌 **Folio / Ticket / AIRIS:** `{folio_input.strip()}`"
            )
            if comentario_adjunto.strip():
              mensaje_final += f"\n\n{comentario_adjunto.strip()}"

            nuevo_registro = {
                "canal": "general",
                "emisor": st.session_state.sf_chat_user,
                "mensaje": mensaje_final,
                "destinatario": None,
                "url_adjunto": url_adjunto_final,
            }

            try:
              supabase.table("mensajes").insert(nuevo_registro).execute()
              st.session_state.upload_counter += 1
              st.rerun()
            except Exception as write_err:
              st.error(f"🔴 Error al enviar evidencia: {write_err}")

  # 6. Entrada para Mensajes Tradicionales (Texto)
  prompt = st.chat_input("Escribe un mensaje de texto para SF Pangea...")

  if prompt:
    nuevo_registro = {
        "canal": "general",
        "emisor": st.session_state.sf_chat_user,
        "mensaje": prompt,
        "destinatario": None,
        "url_adjunto": None,
    }

    try:
      supabase.table("mensajes").insert(nuevo_registro).execute()
      st.rerun()
    except Exception as write_err:
      st.error(f"🔴 Error al enviar mensaje: {write_err}")
