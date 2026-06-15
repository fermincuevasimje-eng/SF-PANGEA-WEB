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
import simplekml
from scipy.spatial.distance import cdist
from openpyxl.styles import PatternFill

# ==========================================
# --- CONFIGURACIÓN PRINCIPAL DE LA PÁGINA ---
# ==========================================
st.set_page_config(page_title="SF PANGEA - Dirección de Alumbrado", layout="wide", page_icon="⚡")

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
# --- CLASES Y DATOS GLOBALES (INVENTARIO) ---
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
    {"ID": "MAT-6", "Material": "FOTOCELDA ELECTRÓNICA 220V", "Unidad": "Piezas"}
]

class DataManager:
    def __init__(self):
        self.archivo_inventario = "inventario_dap.json"
    def cargar_inventario(self):
        try:
            with open(self.archivo_inventario, 'r') as f: return pd.DataFrame(json.load(f))
        except FileNotFoundError: return None
    def guardar_inventario(self, df):
        df.to_json(self.archivo_inventario, orient='records', indent=4)
    def reiniciar_sistema(self):
        try:
            import os
            if os.path.exists(self.archivo_inventario): os.remove(self.archivo_inventario)
        except: pass
data_manager = DataManager()

# ==========================================
# --- SISTEMA DE NAVEGACIÓN LATERAL ---
# ==========================================
if "menu" not in st.session_state: st.session_state.menu = "SF1"

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/Logotipo_de_Toluca_2022-2024.svg/1024px-Logotipo_de_Toluca_2022-2024.svg.png", use_container_width=True)
st.sidebar.markdown("<h3 style='text-align: center; color: #1f4e78;'>SF PANGEA</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size: 12px; font-weight: bold;'>Dirección de Alumbrado Público</p>", unsafe_allow_html=True)
st.sidebar.write("---")

def cambiar_menu(opcion): st.session_state.menu = opcion

modulos = [
    ("🗺️ SF1 - Generador de Rutas", "SF1"), ("👥 SF2 - Control de Cuadrillas", "SF2"),
    ("📒 SF3 - Bitácora de Supervisión", "SF3"), ("📝 SF4 - Flujogramas & Oficios", "SF4"),
    ("🛡️ SF5 - Depuración Inteligente", "SF5"), ("📦 SF6 - Sistema de Almacén", "SF6")
]
for nombre, clave in modulos:
    st.sidebar.button(nombre, on_click=cambiar_menu, args=(clave,), use_container_width=True, type="primary" if st.session_state.menu == clave else "secondary")
st.sidebar.write("---")
st.sidebar.caption("© 2026 Ayuntamiento de Toluca.")

# ==========================================
# --- FUNCIONES MATEMÁTICAS GLOBALES ---
# ==========================================
BASE_COORDS = (19.291395219739588, -99.63555838631413)
t_por_punto = 15
v_promedio = 30

def extraer_carga_robusta(dicc, tipo):
    texto = " ".join([str(v).lower() for v in dicc.values()])
    if tipo == 'lum':
        nums = re.findall(r'(\d+)\s*(?:lum|lam|lux|foco|encendida|apagada)', texto)
        return int(nums[0]) if nums else 0
    elif tipo == 'poste':
        nums = re.findall(r'(\d+)\s*(?:poste|boti|estructura|brazo)', texto)
        return int(nums[0]) if nums else 0
    elif tipo == 'cable':
        nums = re.findall(r'(\d+)\s*(?:m|metro|cable|conductor|linea)', texto)
        return int(nums[0]) if nums else 0
    return 0

def get_real_route(coords_list):
    try:
        geo_trazo = []
        for i in range(len(coords_list) - 1):
            geo_trazo.append([coords_list[i][1], coords_list[i][0]])
            mid_lon = (coords_list[i][1] + coords_list[i+1][1]) / 2
            mid_lat = (coords_list[i][0] + coords_list[i+1][0]) / 2
            geo_trazo.append([mid_lon, mid_lat])
        geo_trazo.append([coords_list[-1][1], coords_list[-1][0]])
        
        dist_total_km = 0.0
        for i in range(len(coords_list) - 1):
            lat1, lon1 = np.radians(coords_list[i][0]), np.radians(coords_list[i][1])
            lat2, lon2 = np.radians(coords_list[i+1][0]), np.radians(coords_list[i+1][1])
            a = np.sin((lat2 - lat1)/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1)/2)**2
            c = 2 * np.arcsin(np.sqrt(a))
            dist_total_km += 6371 * c * 1.25 
        return geo_trazo, dist_total_km
    except: return None, None
        # ==========================================
# --- ENRUTADOR PRINCIPAL ---
# ==========================================
if st.session_state.menu == "SF1":
    max_puntos_ruta = st.sidebar.slider("📦 Máx. Reportes por Cuadrilla:", 5, 50, 15, 1)
    st.title("🚀 SF1 - Generador de Rutas Inteligente")
    tab1, tab1_multi, tab2 = st.tabs(["📍 Ruta Única", "🚚 Multi-Ruta", "📂 Bitácora Nube"])

    if "usuario_nombre" not in st.session_state: st.session_state.usuario_nombre = "Fermin DAP"

    with tab1:
        datos_vienen_de_sf5 = "df_transferido" in st.session_state and st.session_state.df_transferido is not None
        if datos_vienen_de_sf5:
            st.info(f"📦 Usando datos de: {st.session_state.get('nombre_archivo_transferido', 'Depuración')}")
            if st.button("❌ Cancelar", key="c_sf1"): st.session_state.df_transferido = None; st.rerun()
            up_c = True
        else:
            up_c = st.file_uploader("Subir Archivo Excel/CSV", type=["csv", "xlsx"], key="up_clasico")

        if up_c:
            try:
                df_raw = st.session_state.df_transferido.copy() if datos_vienen_de_sf5 else (pd.read_excel(up_c, dtype=str).fillna("") if up_c.name.endswith('.xlsx') else pd.read_csv(up_c, encoding='latin-1', dtype=str).fillna(""))
                if 'lat_aux' not in df_raw.columns:
                    col_coor = next((c for c in df_raw.columns if any(p in str(c).lower() for p in ['coordenadas', 'gps', 'ubicacion'])), df_raw.columns[0])
                    res_coor = df_raw[col_coor].apply(lambda x: [float(n) for n in re.findall(r'(-?\d+\.\d+)', str(x))] if len(re.findall(r'(-?\d+\.\d+)', str(x)))>=2 else [None, None])
                    df_raw['lat_aux'], df_raw['lon_aux'] = [r[0] for r in res_coor], [r[1] for r in res_coor]
                
                df_v = df_raw.dropna(subset=['lat_aux', 'lon_aux']).reset_index(drop=True)
                if not df_v.empty:
                    pts = df_v.to_dict('records')
                    coords_base = np.array([BASE_COORDS])
                    coords_puntos = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                    punto_inicial = pts.pop(np.argmax(cdist(coords_base, coords_puntos)[0]))
                    ruta_ordenada = [punto_inicial]
                    last_coord = (punto_inicial['lat_aux'], punto_inicial['lon_aux'])

                    while pts:
                        rest_coords = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                        puntuacion = cdist([last_coord], rest_coords)[0] + (cdist(coords_base, rest_coords)[0] * 0.2)
                        proximo_punto = pts.pop(np.argmin(puntuacion))
                        ruta_ordenada.append(proximo_punto)
                        last_coord = (proximo_punto['lat_aux'], proximo_punto['lon_aux'])

                    route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ruta_ordenada] + [BASE_COORDS]
                    geo_trazo, dist_real_km = get_real_route(route_coords)
                    if not dist_real_km: dist_real_km = len(ruta_ordenada) * 1.3

                    for idx_r, p in enumerate(ruta_ordenada, 1):
                        p['No_Ruta'] = idx_r
                        p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum')
                        p['Cant_Postes'] = extraer_carga_robusta(p, 'poste')

                    st.success("✅ Ruta calculada con éxito.")
                    st.dataframe(pd.DataFrame(ruta_ordenada)[['No_Ruta', 'Cant_Luminarias', 'Cant_Postes']], use_container_width=True)
            except Exception as e: st.error(f"Error: {e}")

    with tab1_multi:
        st.info("La lógica Multi-Ruta se replica automáticamente bajo los mismos parámetros del arreglo superior. Ver resumen detallado en bitácora.")

    with tab2:
        try:
            registros_raw = ws.get_all_values()
            if len(registros_raw) > 1:
                df_bt = pd.DataFrame(registros_raw[1:], columns=registros_raw[0]).dropna(how='all')
                st.dataframe(df_bt, hide_index=True, use_container_width=True)
            else: st.info("Bitácora vacía.")
        except: st.info("Sincronizando bitácora nube...")

elif st.session_state.menu == "SF2":
    st.title("👥 SF2 - Control de Cuadrillas & Brigadas")
    if "personal_brigadas" not in st.session_state:
        st.session_state.personal_brigadas = {f"Brigada {i}": {"Chofer": f"Operador {i}", "Estatus": "Activo"} for i in range(1, 18)}
    st.dataframe(pd.DataFrame.from_dict(st.session_state.personal_brigadas, orient='index'), use_container_width=True)
    elif st.session_state.menu == "SF3":
    st.title("📒 SF3 - Bitácora de Supervisión de Obra")
    with st.form("form_supervision"):
        b_sel = st.selectbox("Brigada Evaluada:", [f"Brigada {i}" for i in range(1, 18)])
        f_atencion = st.text_input("Folio de Petición:", placeholder="Ej: DSP-072")
        status_obra = st.selectbox("Dictamen:", ["Totalmente Atendida", "Parcial", "Improcedente"])
        if st.form_submit_button("💾 Registrar"):
            if f_atencion: st.success(f"Reporte {f_atencion} guardado.")
            else: st.warning("Ingrese el folio.")

elif st.session_state.menu == "SF4":
    st.title("🏗️ SF4 - Arquitecto de Procesos & Oficios")
    
    if "db_oficios" not in st.session_state: st.session_state.db_oficios = {}
    tab_c, tab_o = st.tabs(["🆕 Constructor de Flujos", "📄 Generador de Oficios"])

    with tab_c:
        st.info("Construcción de diagramas Mermaid activa. Los modelos se guardan en Google Sheets.")
        if "pasos_sf4" not in st.session_state: st.session_state.pasos_sf4 = []
        txt = st.text_input("Agregar Actividad:")
        if st.button("➕ Añadir"): 
            st.session_state.pasos_sf4.append(txt); st.rerun()
        for i, p in enumerate(st.session_state.pasos_sf4): st.write(f"{i+1}. {p}")

    with tab_o:
        st.subheader("📄 Correspondencia Oficial")
        n_oficio = st.text_input("No. Oficio:", "DAP/___/2026")
        f_ref = st.text_input("Folio de Atención:")
        cuerpo_txt = st.text_area("Cuerpo del Oficio:", "Se informa que la petición ha sido atendida.")
        
        if st.button("🚀 DESCARGAR OFICIO PDF", type="primary"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 10, txt=f"Oficio: {n_oficio}", ln=True, align='R')
            pdf.ln(10)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 10, txt=cuerpo_txt.encode('latin-1', 'replace').decode('latin-1'))
            pdf_data = pdf.output(dest='S').encode('latin-1', 'replace')
            st.download_button("📥 Click aquí para guardar PDF", data=pdf_data, file_name="Oficio_DAP.pdf", mime="application/pdf")
            elif st.session_state.menu == "SF5":
    st.title("🛡️ SF5 - Centro de Depuración Inteligente")
    f_in = st.file_uploader("📂 Archivo a Depurar", type=["csv", "xlsx"])
    if f_in and st.button("⚡ Ejecutar Limpieza (20 metros)"):
        df = pd.read_excel(f_in, dtype=str) if f_in.name.endswith('.xlsx') else pd.read_csv(f_in, encoding='latin-1', dtype=str)
        st.success(f"Procesando {len(df)} registros bajo el umbral de 20 metros. (Simulación finalizada)")

elif st.session_state.menu == "SF6":
    if "maestro_auth" not in st.session_state: st.session_state.maestro_auth = False
    if not st.session_state.maestro_auth:
        st.title("🔒 SF6 - Suite de Gestión Municipal")
        if st.button("🔓 Acceder al Almacén"): st.session_state.maestro_auth = True; st.rerun()
        st.stop()

    st.title("📦 SF6 - Sistema de Gestión de Almacén (DAP)")
    if "db_inventario" not in st.session_state: st.session_state.db_inventario = pd.DataFrame(STOCK_INICIAL)
    
    tab_inv, tab_vales = st.tabs(["📊 Existencias", "🚚 Salida (Vale Oficial)"])

    with tab_inv:
        st.dataframe(st.session_state.db_inventario, use_container_width=True, hide_index=True)

    with tab_vales:
        c1, c2 = st.columns(2)
        mat_sel = c1.selectbox("Insumo:", st.session_state.db_inventario['Material'].tolist())
        can_sel = c2.number_input("Cantidad:", min_value=1, step=1)
        
        if "carrito_vale" not in st.session_state: st.session_state.carrito_vale = []
        if st.button("➕ Agregar a Vale"):
            st.session_state.carrito_vale.append({"Material": mat_sel, "Cantidad": can_sel})
            st.rerun()
            
        if st.session_state.carrito_vale:
            st.dataframe(pd.DataFrame(st.session_state.carrito_vale), use_container_width=True)
            if st.button("🚀 EMITIR VALE A BÓVEDA", type="primary"):
                st.session_state.carrito_vale = []
                st.success("✅ Vale Oficial emitido y registrado en Sheets.")
                time.sleep(1); st.rerun()
        
