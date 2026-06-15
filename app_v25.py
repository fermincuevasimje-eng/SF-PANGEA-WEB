import streamlit as st
import pandas as pd
import numpy as np
import json
import io
import base64
import time
import re
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium
import plotly.express as px
from openpyxl.styles import PatternFill

# ==========================================
# --- CONFIGURACIÓN PRINCIPAL DE LA PÁGINA ---
# ==========================================
st.set_page_config(page_title="SF PANGEA - Dirección de Alumbrado", layout="wide", page_icon="⚡")

# ==========================================
# --- ESTILOS CSS GLOBALES ---
# ==========================================
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    h1 {color: #1f4e78; font-weight: 700;}
    h2, h3 {color: #2c3e50;}
    .stButton>button {
        background-color: #1f4e78; color: white; border-radius: 8px; font-weight: 600;
        transition: all 0.3s; width: 100%; border: none; padding: 0.5rem 1rem;
    }
    .stButton>button:hover {background-color: #153a5b; transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1);}
    .metric-card {
        background: white; border-radius: 10px; padding: 20px; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #1f4e78;
    }
    .css-1d391kg {padding-top: 1rem;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# --- CONEXIÓN MAESTRA A GOOGLE SHEETS ---
# ==========================================
@st.cache_resource(show_spinner="Iniciando enlace seguro con GSheets...")
def init_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"].replace('\\n', '\n'),
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
    }
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

try:
    client = init_connection()
    SHEET_ID = "14_fewol5DiFXoiO102wviiWR08Lw3PKHzEjSbMwxUm8"
    sh = client.open_by_key(SHEET_ID)
    ws = sh.worksheet("Boveda_Bajas")
except Exception as e:
    st.error(f"Error crítico al conectar con la bóveda de Google Sheets: {e}")
    st.stop()

# ==========================================
# --- CLASES Y DATOS GLOBALES (INVENTARIO Y ALMACÉN) ---
# ==========================================
class Config:
    PIN_ALMACEN = "2026"

config = Config()

STOCK_INICIAL = [
    {"ID": "MAT-1", "Material": "LUMINARIA LED 100W", "Unidad": "Piezas"},
    {"ID": "MAT-2", "Material": "CABLE DE ALUMINIO CALIBRE 6", "Unidad": "Metros"},
    {"ID": "MAT-3", "Material": "CINTA DE AISLAR NEGRA SUPER 33", "Unidad": "Piezas"},
    {"ID": "MAT-4", "Material": "BRAZO METÁLICO PARA LUMINARIA 1.5M", "Unidad": "Piezas"},
    {"ID": "MAT-5", "Material": "ABRAZADERA OMEGA", "Unidad": "Piezas"},
    {"ID": "MAT-6", "Material": "FOTOCELDA ELECTRÓNICA 220V", "Unidad": "Piezas"},
    {"ID": "MAT-7", "Material": "CONECTOR PONCHABLE", "Unidad": "Piezas"},
    {"ID": "MAT-8", "Material": "POSTE METÁLICO 9 METROS", "Unidad": "Piezas"},
    {"ID": "MAT-9", "Material": "REFLECTOR LED 200W", "Unidad": "Piezas"},
    {"ID": "MAT-10", "Material": "BASE PARA FOTOCELDA", "Unidad": "Piezas"}
]

class DataManager:
    def __init__(self):
        self.archivo_inventario = "inventario_dap.json"
    
    def cargar_inventario(self):
        try:
            with open(self.archivo_inventario, 'r') as f:
                return pd.DataFrame(json.load(f))
        except FileNotFoundError:
            return None
            
    def guardar_inventario(self, df):
        df.to_json(self.archivo_inventario, orient='records', indent=4)
        
    def reiniciar_sistema(self):
        try:
            import os
            if os.path.exists(self.archivo_inventario):
                os.remove(self.archivo_inventario)
        except Exception as e:
            st.error(f"Error al reiniciar: {e}")

data_manager = DataManager()

# ==========================================
# --- SISTEMA DE NAVEGACIÓN Y BARRA LATERAL ---
# ==========================================
if "menu" not in st.session_state:
    st.session_state.menu = "SF1"

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/Logotipo_de_Toluca_2022-2024.svg/1024px-Logotipo_de_Toluca_2022-2024.svg.png", use_container_width=True)
st.sidebar.markdown("<h3 style='text-align: center; color: #1f4e78;'>SF PANGEA</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size: 12px; font-weight: bold;'>Dirección de Alumbrado Público</p>", unsafe_allow_html=True)
st.sidebar.write("---")

def cambiar_menu(opcion):
    st.session_state.menu = opcion

st.sidebar.button("🗺️ SF1 - Generador de Rutas", on_click=cambiar_menu, args=("SF1",), use_container_width=True, type="primary" if st.session_state.menu == "SF1" else "secondary")
st.sidebar.button("👥 SF2 - Control de Cuadrillas", on_click=cambiar_menu, args=("SF2",), use_container_width=True, type="primary" if st.session_state.menu == "SF2" else "secondary")
st.sidebar.button("📒 SF3 - Bitácora de Supervisión", on_click=cambiar_menu, args=("SF3",), use_container_width=True, type="primary" if st.session_state.menu == "SF3" else "secondary")
st.sidebar.button("📝 SF4 - Flujogramas & Oficios", on_click=cambiar_menu, args=("SF4",), use_container_width=True, type="primary" if st.session_state.menu == "SF4" else "secondary")
st.sidebar.button("🛡️ SF5 - Depuración Inteligente", on_click=cambiar_menu, args=("SF5",), use_container_width=True, type="primary" if st.session_state.menu == "SF5" else "secondary")
st.sidebar.button("📦 SF6 - Sistema de Almacén", on_click=cambiar_menu, args=("SF6",), use_container_width=True, type="primary" if st.session_state.menu == "SF6" else "secondary")

st.sidebar.write("---")
st.sidebar.caption("© 2026 Ayuntamiento de Toluca.")

# ==========================================
# --- ENRUTADOR DE MÓDULOS ---
# ==========================================
