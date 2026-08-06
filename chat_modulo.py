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


# Helper para consultar usuarios registrados
def obtener_usuarios_chat(supabase_client, usuario_actual: str) -> list:
  try:
    res = supabase_client.table("mensajes").select("emisor").execute()
    if res.data:
      emisores = {
          fila.get("emisor")
          for fila in res.data
          if fila.get("emisor") and fila.get("emisor") != usuario_actual
      }
      return sorted(list(emisores))
    return []
  except Exception:
    return []


# -----------------------------------------------------------------------------
# FASE 3 + PANELES FIJOS + FILTROS DE FECHA Y HORA (2s)
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
):
  supabase = get_supabase_client()

  def cargar_historial():
    try:
      query = supabase.table("mensajes").select("*")

      if solo_menciones:
        res = query.order("created_at", desc=True).execute()
        data = res.data if res.data else []
        tag = f"@{usuario_actual.lower()}"
        data = [
            m
            for m in data
            if tag in m.get("mensaje", "").lower()
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
        res = query.eq("canal", canal).order("created_at", desc=False).execute()
        data = res.data if res.data else []

      # Filtrado por Fecha y Hora (si se activó en la interfaz)
      if fecha_filtro and data:
        data_filtrada = []
        for m in data:
          raw_time = m.get("created_at", "")
          if raw_time:
            try:
              dt_utc = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
              dt_local = dt_utc.astimezone(ZoneInfo("America/Mexico_City"))

              if dt_local.date() == fecha_filtro:
                if hora_inicio and hora_fin:
                  if hora_inicio <= dt_local.time() <= hora_fin:
                    data_filtrada.append(m)
                else:
                  data_filtrada.append(m)
            except Exception:
              pass
        return data_filtrada

      return data
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

  hora_actual = datetime.now(ZoneInfo("America/Mexico_City")).strftime(
      "%H:%M:%S"
  )
  if solo_menciones:
    st.caption(
        f"🔔 **Muro de Menciones para @{usuario_actual}** • En vivo"
        f" (`{hora_actual}`)"
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

  # Contenedor con altura fija y scroll interno independiente para congelar el menú superior
  chat_container = st.container(height=500)
  with chat_container:
    if mensajes:
      for msg_idx, fila in enumerate(mensajes):
        usr = fila.get("emisor", "Anónimo")
        msg = fila.get("mensaje", "")
        url_adjunto_raw = fila.get("url_adjunto", None)
        canal_origen = fila.get("canal", "general")

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

        mencion_tag = f"@{usuario_actual.lower()}"
        contiene_mencion = mencion_tag in msg.lower() and not es_propio

        with st.chat_message(usr, avatar=avatar_icon):
          if contiene_mencion and not solo_menciones:
            st.warning(f"🔔 **¡{usr} te ha mencionado en este mensaje!**")

          if solo_menciones:
            st.info(f"📌 Mencionado en canal: **#{canal_origen.upper()}**")

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
                        key=f"dl_btn_{msg_idx}_{file_idx}_{canal}",
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
                        key=f"dl_btn_file_{msg_idx}_{file_idx}_{canal}",
                    )
                with col_btn2:
                  st.link_button(
                      "🌐 Abrir en pestaña",
                      url_adjunto,
                      use_container_width=True,
                  )
    else:
      st.info("No hay mensajes para el filtro o fecha seleccionados.")


# -----------------------------------------------------------------------------
# Función Principal del Módulo
# -----------------------------------------------------------------------------
def render_chat():
  st.header("💬 SF Pangea Chat")
  st.caption("Módulo de comunicación interna seguro y optimizado con Supabase")

  supabase = get_supabase_client()

  # Control de Usuario y Formulario
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

  # Barra superior de sesión
  col_status, col_logout = st.columns([4, 1])
  with col_status:
    st.success(f"🟢 Usuario activo: **{st.session_state.sf_chat_user}**")
  with col_logout:
    if st.button("Cambiar usuario", key="sf_chat_btn_logout"):
      st.session_state.sf_chat_user = ""
      st.rerun()

  # ---------------------------------------------------------------------------
  # ORGANIZACIÓN POR PESTAÑAS (TABS) - RÁPIDO Y CÓMODO
  # ---------------------------------------------------------------------------
  tab_canales, tab_privados, tab_menciones = st.tabs([
      "📢 Canales Públicos",
      "🔒 Chat 1 a 1 (Privado)",
      "🔔 Mis Menciones",
  ])

  # --- PESTAÑA 1: CANALES PÚBLICOS ---
  with tab_canales:
    canal_seleccionado = st.radio(
        "Canal activo:",
        ["General", "Mantenimiento", "Infraestructura", "DAP"],
        horizontal=True,
        key="sf_chat_radio_canal",
    )
    canal_activo = canal_seleccionado.lower()

    # Filtro por Fecha y Hora opcional para Canales
    f_fecha_c, f_h_ini_c, f_h_fin_c = None, None, None
    with st.expander("📅 Filtrar canal por fecha / hora (Opcional)"):
      c1_c, c2_c = st.columns(2)
      with c1_c:
        if st.checkbox("Activar filtro de fecha", key="chk_f_canales"):
          f_fecha_c = st.date_input("Selecciona día:", key="date_canales")
      with c2_c:
        if f_fecha_c and st.checkbox(
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

    render_historial_fragment(
        st.session_state.sf_chat_user,
        canal=canal_activo,
        fecha_filtro=f_fecha_c,
        hora_inicio=f_h_ini_c,
        hora_fin=f_h_fin_c,
    )

    # Controles de envío para Pestaña 1
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
            "Comentario (Opcional):", key=f"sf_chat_comentario_canales_{count}"
        )
        if st.button(
            "Enviar Evidencias 🚀",
            key=f"btn_enviar_canales_{count}",
            use_container_width=True,
        ):
          if not folio_input.strip():
            st.error("⚠️ Debes ingresar el Folio / Ticket / AIRIS.")
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

  # --- PESTAÑA 2: CHAT PRIVADO 1 A 1 ---
  with tab_privados:
    usuarios_disponibles = obtener_usuarios_chat(
        supabase, st.session_state.sf_chat_user
    )
    if usuarios_disponibles:
      destinatario_activo = st.selectbox(
          "👤 Selecciona el colega para chatear en privado:",
          usuarios_disponibles,
          key="sf_chat_select_privado",
      )

      render_historial_fragment(
          st.session_state.sf_chat_user,
          canal="privado",
          destinatario=destinatario_activo,
      )

      count = st.session_state.upload_counter
      with st.popover(f"📎 Adjuntar archivo privado para {destinatario_activo}"):
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
              "Comentario (Opcional):", key=f"sf_chat_coment_priv_{count}"
          )
          if st.button(
              "Enviar Evidencia Privada 🚀",
              key=f"btn_enviar_priv_{count}",
              use_container_width=True,
          ):
            if not folio_priv.strip():
              st.error("⚠️ Debes ingresar el Folio / Ticket / AIRIS.")
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
      st.info(
          "💡 Aún no hay otros usuarios registrados en el historial para conversar"
          " en privado."
      )

  # --- PESTAÑA 3: MIS MENCIONES Y ALERTAS ---
  with tab_menciones:
    f_fecha_m, f_h_ini_m, f_h_fin_m = None, None, None
    with st.expander("📅 Filtrar menciones por fecha / hora (Opcional)"):
      c1_m, c2_m = st.columns(2)
      with c1_m:
        if st.checkbox("Activar filtro de fecha", key="chk_f_menciones"):
          f_fecha_m = st.date_input("Selecciona día:", key="date_menciones")
      with c2_m:
        if f_fecha_m and st.checkbox(
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
    )
