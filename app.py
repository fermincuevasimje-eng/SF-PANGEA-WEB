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
import json

# ==========================================================
# SF PANGEA v4.4.1 - TOLUCA ELITE (REVISADO)
# ==========================================================

st.set_page_config(page_title="SF PANGEA - Toluca", page_icon="🚀", layout="wide")

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #611232 !important; }
    .stMarkdown h1, h2, h3 { color: #611232 !important; }
    .stButton>button { background-color: #A57F2C !important; color: white !important; border: none; width: 100%; }
    .stMetric { border-left: 5px solid #A57F2C !important; background-color: #f9f9f9; padding: 15px; border-radius: 10px; }
    div[data-testid="stSidebar"] .stMarkdown p { color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- USUARIOS ---
usuarios_db = {
    "SF": {"password": "1827", "rol": "admin"},
    "GuaDAP": {"password": "5555", "rol": "consulta"}
}

# --- CONEXIÓN ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("⚠️ Error de conexión con Google Sheets.")

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
    with st.sidebar:
        st.image("https://www.toluca.gob.mx/wp-content/uploads/2019/08/escudo-blanco.png", width=180)
        st.markdown(f"### 👤 {st.session_state.user}")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
        t_min = st.number_input("Minutos por Punto", value=20)
        v_kmh = st.number_input("Velocidad km/h", value=25)

    BASE_COORDS = (19.291395219739588, -99.63555838631413)

    def get_route(coords):
        # Aquí estaba el error de la llave en la línea de abajo:
        locs = ";".join([f"{lon},{lat}" for lat, lon in coords])
        url = f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                r = response.json()
                if r.get('code') == 'Ok':
                    return r['routes'][0]['geometry']['coordinates'], r['routes'][0]['distance']/1000
            return [(c[1], c[0]) for c in coords], len(coords) * 1.3
        except:
            return [(c[1], c[0]) for c in coords], len(coords) * 1.5

    if st.session_state.rol == "admin":
        st.header("🛠️ Panel de Administración")
        up = st.file_uploader("Cargar Reporte (Excel o CSV)", type=["xlsx", "csv"])
        
        if up:
            df = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
            res_gps = df.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df['lat_aux'], df['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                pts = df_v.to_dict('records')
                idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
                ordenados = [pts.pop(idx_lejano)]
                while pts:
                    rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                    idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                    ordenados.append(pts.pop(idx))

                route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                trazo, dist_km = get_route(route_coords)

                m = folium.Map(location=BASE_COORDS, zoom_start=13)
                for i, p in enumerate(ordenados, 1):
                    folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {i}").add_to(m)
                if trazo:
                    folium.PolyLine([(c[1], c[0]) for c in trazo], color="#611232", weight=5).add_to(m)
                st_folium(m, width=900, height=450)

                if st.button("💾 GUARDAR RUTA"):
                    try:
                        nueva = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Nombre_Ruta": up.name, "Usuario": st.session_state.user, "Datos_JSON": json.dumps(ordenados)}])
                        ex = conn.read()
                        conn.update(data=pd.concat([ex, nueva], ignore_index=True))
                        st.success("Guardado con éxito.")
                    except: st.error("Error al guardar.")

    st.markdown("---")
    st.header("🔍 Buscador de Rutas")
    try:
        df_bd = conn.read()
        if not df_bd.empty:
            sel = st.selectbox("Rutas guardadas:", ["-- Seleccionar --"] + df_bd["Nombre_Ruta"].tolist())
            if sel != "-- Seleccionar --":
                fila = df_bd[df_bd["Nombre_Ruta"] == sel].iloc[-1]
                puntos = json.loads(fila["Datos_JSON"])
                st.dataframe(pd.DataFrame(puntos).drop(columns=['lat_aux', 'lon_aux']))
                kml = simplekml.Kml()
                for p in puntos: kml.newpoint(name=str(p.get('ID_Pangea_Nombre', 'Punto')), coords=[(p['lon_aux'], p['lat_aux'])])
                st.download_button(f"🗺️ Descargar KML", kml.kml(), f"{sel}.kml")
    except: st.info("Esperando datos...")
