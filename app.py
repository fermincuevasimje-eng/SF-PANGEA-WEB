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
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill
import json

# ==========================================================
# SF PANGEA v4.4.1 - TOLUCA ELITE (ESTABLE)
# ==========================================================

st.set_page_config(page_title="SF PANGEA - Toluca", page_icon="🚀", layout="wide")

# --- ESTILO VISUAL INSTITUCIONAL ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #611232 !important; }
    .stMarkdown h1, h2, h3 { color: #611232 !important; }
    .stButton>button { background-color: #A57F2C !important; color: white !important; border: none; width: 100%; }
    .stMetric { border-left: 5px solid #A57F2C !important; background-color: #f9f9f9; padding: 15px; border-radius: 10px; }
    div[data-testid="stSidebar"] .stMarkdown p { color: white !important; font-weight: bold; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS DE USUARIOS ---
usuarios_db = {
    "SF": {"password": "1827", "rol": "admin"},
    "GuaDAP": {"password": "5555", "rol": "consulta"}
}

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("⚠️ Error de conexión con Google Sheets. Verifica los 'Secrets' en Streamlit.")

def login():
    if "autenticado" not in st.session_state: st.session_state.autenticado = False
    if not st.session_state.autenticado:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Logotipo_del_Ayuntamiento_de_Toluca.svg/1200px-Logotipo_del_Ayuntamiento_de_Toluca.svg.png", width=250)
            st.title("🔐 Acceso SF PANGEA")
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar al Sistema"):
                if u in usuarios_db and usuarios_db[u]["password"] == p:
                    st.session_state.autenticado, st.session_state.rol, st.session_state.user = True, usuarios_db[u]["rol"], u
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
        return False
    return True

if login():
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.image("https://www.toluca.gob.mx/wp-content/uploads/2019/08/escudo-blanco.png", width=180)
        st.markdown(f"### 👤 {st.session_state.user}")
        st.markdown(f"**Rol:** {st.session_state.rol.upper()}")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
        st.markdown("---")
        t_min = st.number_input("Minutos por Punto", value=20)
        v_kmh = st.number_input("Velocidad km/h", value=25)

    BASE_COORDS = (19.291395219739588, -99.63555838631413)

    # --- FUNCIÓN DE RUTA ROBUSTA (Antifallas) ---
    def get_route(coords):
        locs = ";".join([f"{lon},{
