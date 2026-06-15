import streamlit as st
import pandas as pd
import numpy as np
import json
import io
import base64
import time
import re
from datetime import datetime, timedelta, timezone
from fpdf import FPDF
import gspread
from google.oauth2.service_account import Credentials
from scipy.spatial.distance import cdist

st.set_page_config(page_title="SF PANGEA - DAP", layout="wide")

# --- CONEXIÓN A NUBE ---
@st.cache_resource
def init_connection():
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
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

client = init_connection()
ws = client.open_by_key("14_fewol5DiFXoiO102wviiWR08Lw3PKHzEjSbMwxUm8").worksheet("Boveda_Bajas")

# --- MENÚ ---
if "menu" not in st.session_state: st.session_state.menu = "SF1"
st.sidebar.title("SF PANGEA DAP")
menu_opciones = ["SF1", "SF2", "SF3", "SF4", "SF5", "SF6"]
for op in menu_opciones:
    if st.sidebar.button(op): st.session_state.menu = op; st.rerun()

# --- LÓGICA DE MÓDULOS ---
if st.session_state.menu == "SF1":
    st.title("🚀 SF1 - Generador de Rutas")
    st.write("Generador activo.")

elif st.session_state.menu == "SF2":
    st.title("👥 SF2 - Control de Cuadrillas")
    st.write("Panel de brigadas.")

elif st.session_state.menu == "SF3":
    st.title("📒 SF3 - Bitácora")
    st.write("Bitácora de supervisión.")

elif st.session_state.menu == "SF4":
    st.title("🏗️ SF4 - Oficios")
    st.write("Generador de documentos.")

elif st.session_state.menu == "SF5":
    st.title("🛡️ SF5 - Depuración")
    st.write("Motor de limpieza GPS.")

elif st.session_state.menu == "SF6":
    st.title("📦 SF6 - Almacén")
    if "maestro_auth" not in st.session_state: st.session_state.maestro_auth = False
    
    if not st.session_state.maestro_auth:
        pin = st.text_input("PIN Maestro:", type="password")
        if st.button("Acceder"):
            if pin == "1827": st.session_state.maestro_auth = True; st.rerun()
            else: st.error("PIN Incorrecto")
    else:
        st.write("Bienvenido al sistema de almacén.")
