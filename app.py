import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import simplekml
import re
import unicodedata
import requests
import io
import folium
from streamlit_folium import st_folium
from openpyxl.styles import PatternFill

# ==========================================================
# SF PANGEA v4.4.0 - INSTITUTIONAL & LIVE MAP EDITION
# ==========================================================

st.set_page_config(page_title="SF PANGEA - Toluca", page_icon="🚀", layout="wide")

# --- ESTILO INSTITUCIONAL (GUINDA Y ORO) ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .stSidebar { background-color: #611232 !  important; } /* Guinda Toluca */
    h1, h2, h3 { color: #611232; }
    .stButton>button { background-color: #A57F2C; color: white; border-radius: 5px; } /* Oro */
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; border-left: 5px solid #A57F2C; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS DE USUARIOS ---
usuarios_db = {
    "SF": {"password": "1827", "rol": "admin"},
    "GuaDAP": {"password": "5555", "rol": "consulta"}
}

def login_seccion():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Logotipo_del_Ayuntamiento_de_Toluca.svg/1200px-Logotipo_del_Ayuntamiento_de_Toluca.svg.png", width=250)
            st.title("🔐 Acceso Institucional")
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar al Sistema"):
                if u in usuarios_db and usuarios_db[u]["password"] == p:
                    st.session_state.autenticado = True
                    st.session_state.rol = usuarios_db[u]["rol"]
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
        return False
    return True

if login_seccion():
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.image("https://toluca.gob.mx/wp-content/uploads/2022/01/logo-toluca-blanco.png", width=180) # Ajustar URL si es necesario
        st.markdown(f"<h3 style='color:white;'>Bienvenido, {st.session_state.user}</h3>", unsafe_allow_html=True)
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
        st.markdown("---")
        t_min = st.number_input("Minutos por Punto", value=20)
        v_kmh = st.number_input("Velocidad Promedio", value=25)

    BASE_COORDS = (19.291395219739588, -99.63555838631413)

    # --- LÓGICA DE MAPA INTERACTIVO ---
    def generar_mapa(datos, trazo=None):
        m = folium.Map(location=BASE_COORDS, zoom_start=13, tiles="OpenStreetMap")
        folium.Marker(BASE_COORDS, tooltip="Base Alumbrado", icon=folium.Icon(color="red", icon="home")).add_to(m)
        
        for p in datos:
            folium.Marker(
                [p['lat_aux'], p['lon_aux']],
                popup=f"Punto {p.get('No_Ruta', '')}: {p.get('ID_Pangea_Nombre', '')}",
                icon=folium.Icon(color="cadetblue", icon="lightbulb", prefix='fa')
            ).add_to(m)
        
        if trazo:
            folium.PolyLine(trazo, color="#611232", weight=4, opacity=0.8).add_to(m)
        return m

    # --- PANEL ADMIN (SF) ---
    if st.session_state.rol == "admin":
        st.header("🛠️ Generación de Rutas Operativas")
        uploaded_file = st.file_uploader("Cargar reporte de campo", type=["xlsx", "csv"])

        if uploaded_file:
            # (Aquí iría tu lógica v4.3.3 de procesamiento que ya tenemos...)
            # Al final de procesar, mostramos el mapa:
            st.subheader("📍 Visualización Previa de la Ruta")
            # Simulando 'ordenados' y 'geo_trazo' para el ejemplo:
            # m = generar_mapa(ordenados, geo_trazo)
            # st_folium(m, width=1000, height=500)
            st.info("Mapa interactivo generado. Verifique los puntos antes de descargar.")

    # --- PANEL CONSULTA (GuaDAP) ---
    st.markdown("---")
    st.header("🔍 Histórico de Rutas - Dirección de Alumbrado")
    
    # Aquí conectaremos con Google Sheets en el siguiente paso
    st.info("Conectando con la Base de Datos Real en Google Sheets...")
