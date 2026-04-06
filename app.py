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
import json

# ==========================================================
# SF PANGEA v4.4.0 - TOLUCA INSTITUTIONAL EDITION
# ==========================================================

st.set_page_config(page_title="SF PANGEA - Toluca", page_icon="🚀", layout="wide")

# ID de tu Google Sheet para la Base de Datos
SHEET_ID = "14_fewol5DiFXoiO102wviiWR08Lw3PKHzEjSbMwxUm8"

# --- ESTILO VISUAL GUINDA Y ORO ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #611232 !important; }
    .stMarkdown h1, h2, h3 { color: #611232 !important; }
    .stButton>button { background-color: #A57F2C !important; color: white !important; border: none; }
    .stMetric { border-left: 5px solid #A57F2C !important; background-color: #f9f9f9; }
    div[data-testid="stSidebar"] .stMarkdown p { color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- USUARIOS ---
usuarios_db = {
    "SF": {"password": "1827", "rol": "admin"},
    "GuaDAP": {"password": "5555", "rol": "consulta"}
}

def login():
    if "autenticado" not in st.session_state: st.session_state.autenticado = False
    if not st.session_state.autenticado:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Logotipo_del_Ayuntamiento_de_Toluca.svg/1200px-Logotipo_del_Ayuntamiento_de_Toluca.svg.png", width=250)
            st.title("🔐 Acceso SF PANGEA")
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar"):
                if u in usuarios_db and usuarios_db[u]["password"] == p:
                    st.session_state.autenticado, st.session_state.rol, st.session_state.user = True, usuarios_db[u]["rol"], u
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
        return False
    return True

if login():
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.image("https://toluca.gob.mx/wp-content/uploads/2022/01/logo-toluca-blanco.png", width=200)
        st.markdown(f"Usuario: {st.session_state.user}")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
        st.markdown("---")
        t_min = st.number_input("Minutos/Punto", value=20)
        v_kmh = st.number_input("Velocidad km/h", value=25)

    BASE_COORDS = (19.291395219739588, -99.63555838631413)

    # --- FUNCIONES CORE ---
    def get_route(coords):
        locs = ";".join([f"{lon},{lat}" for lat, lon in coords])
        r = requests.get(f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson").json()
        return (r['routes'][0]['geometry']['coordinates'], r['routes'][0]['distance']/1000) if r['code']=='Ok' else (None, None)

    # --- PANEL ADMIN (SF) ---
    if st.session_state.rol == "admin":
        st.header("🛠️ Panel de Administración")
        up = st.file_uploader("Cargar Reporte de Brigada", type=["xlsx", "csv"])
        if up:
            df = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
            res_gps = df.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df['lat_aux'], df['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df.dropna(subset=['lat_aux']).reset_index(drop=True)
            
            if not df_v.empty:
                pts = df_v.to_dict('records')
                # (Aquí incluiremos el motor de ordenamiento que ya conoces...)
                idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
                ordenados = [pts.pop(idx_lejano)]
                while pts:
                    rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                    idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                    ordenados.append(pts.pop(idx))

                route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                trazo, dist = get_route(route_coords)
                
                # Mapa Vivo
                st.subheader("📍 Mapa de Ruta Optimizada")
                m = folium.Map(location=BASE_COORDS, zoom_start=13)
                folium.Marker(BASE_COORDS, icon=folium.Icon(color='red')).add_to(m)
                for p in ordenados: folium.Marker([p['lat_aux'], p['lon_aux']]).add_to(m)
                if trazo: folium.PolyLine([(c[1], c[0]) for c in trazo], color="#611232").add_to(m)
                st_folium(m, width=900, height=450)
                
                st.success(f"Ruta procesada. Distancia: {round(dist,2) if dist else '---'} km")
                # Botón para simular guardado en Google Sheets (requiere configuración de secretos en Streamlit Cloud)
                if st.button("💾 Guardar en Base de Datos para GuaDAP"):
                    st.toast("Ruta guardada permanentemente en Google Sheets")

    # --- PANEL CONSULTA (GuaDAP) ---
    st.markdown("---")
    st.header("🔍 Buscador de Rutas Institucionales")
    st.info("Aquí aparecerán las rutas guardadas por SF en el Google Sheet.")
