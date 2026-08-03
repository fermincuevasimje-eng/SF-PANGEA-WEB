import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

def render_chat():
    """
    Módulo de Chat aislado e independiente para SF Pangea.
    Previene consumo excesivo de CPU y colisiones de estado.
    """
    st.header("💬 SF Pangea Chat")
    st.caption("Módulo de comunicación interna seguro y optimizado")

    # 1. Conexión Segura mediante Secrets de Streamlit
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"🔴 Error al conectar con los Secrets de Google Sheets: {e}")
        st.stop()

    # 2. Consulta Protegida con Cache (ttl=10s previene CPU Throttling y peticiones infinitas)
    @st.cache_data(ttl=10, show_spinner=False)
    def cargar_historial():
        try:
            df = conn.read(ttl="10s")
            if df is None or df.empty:
                return pd.DataFrame(columns=["timestamp", "usuario", "mensaje"])
            return df.dropna(how="all")
        except Exception as err:
            st.error(f"🔴 Error de lectura en BD_CHAT_PANGEA (Verifica permisos de Service Account): {err}")
            st.stop()

    # 3. Control de Identificación de Usuario (Session State aislado)
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

    # 4. Carga y Renderizado del Historial
    df_chat = cargar_historial()

    chat_container = st.container()
    with chat_container:
        if not df_chat.empty:
            for _, fila in df_chat.iterrows():
                usr = str(fila.get("usuario", "Anónimo"))
                msg = str(fila.get("mensaje", ""))
                tstamp = str(fila.get("timestamp", ""))

                es_propio = (usr == st.session_state.sf_chat_user)
                avatar_icon = "👤" if es_propio else "💬"

                with st.chat_message(usr, avatar=avatar_icon):
                    st.markdown(f"**{usr}** `<{tstamp}>`\n\n{msg}")
        else:
            st.info("No hay mensajes aún. ¡Sé el primero en escribir!")

    # 5. Entrada y Envío de Nuevos Mensajes
    prompt = st.chat_input("Escribe un mensaje para SF Pangea...")
    if prompt:
        nuevo_registro = pd.DataFrame([{
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": st.session_state.sf_chat_user,
            "mensaje": prompt
        }])

        try:
            # Concatenar nuevo mensaje al historial y guardar en Google Sheets
            df_actualizado = pd.concat([df_chat, nuevo_registro], ignore_index=True)
            conn.update(data=df_actualizado)
            
            # Limpiar caché local para mostrar el mensaje al instante
            st.cache_data.clear()
            st.rerun()
        except Exception as write_err:
            st.error(f"🔴 Error al enviar mensaje: {write_err}")
