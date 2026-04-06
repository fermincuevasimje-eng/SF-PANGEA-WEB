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
# SF PANGEA v4.4.2 - "EL MOTOR 4.3.3" EN LA WEB
# ==========================================================

st.set_page_config(page_title="SF PANGEA - Toluca", page_icon="🚀", layout="wide")

# --- ESTILO INSTITUCIONAL ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #611232 !important; }
    .stMarkdown h1, h2, h3 { color: #611232 !important; }
    .stButton>button { background-color: #A57F2C !important; color: white !important; border: none; }
    .stMetric { border-left: 5px solid #A57F2C !important; background-color: #f9f9f9; padding: 15px; border-radius: 10px; }
    div[data-testid="stSidebar"] .stMarkdown p { color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN MOTOR 4.3.3 ---
BASE_COORDS = (19.291395219739588, -99.63555838631413) #
T_UNIDAD_MIN, V_CIU = 20, 25 #

# --- FUNCIONES DEL MOTOR v4.3.3 ---
def get_real_route(coords_list):
    locs = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
    url = f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10).json()
        if r['code'] == 'Ok':
            return r['routes'][0]['geometry']['coordinates'], r['routes'][0]['distance'] / 1000
    except: return None, None

def normalizar_texto(texto):
    if not isinstance(texto, str): texto = str(texto)
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.lower()

def extraer_carga_robusta(punto_dict, tipo):
    d_letras = {'un ':'1 ','uno ':'1 ','una ':'1 ','dos ':'2 ','tres ':'3 ','cuatro ':'4 ','cinco ':'5 ','seis ':'6 ','siete ':'7 ','ocho ':'8 ','nueve ':'9 ','diez ':'10 '}
    posibles_cols = ['ASUNTO', 'Observaciones', 'asunto', 'observaciones', 'Asunto']
    texto_fuente = ""
    for col in posibles_cols:
        if col in punto_dict and str(punto_dict[col]).strip() != "":
            texto_fuente = str(punto_dict[col])
            break
    t_norm = normalizar_texto(texto_fuente)
    for p, n in d_letras.items(): t_norm = t_norm.replace(p, n)
    patrones = {
        'lum': r'(\d+)\s*(?:lampara|foco|reflector|arbotante|luminari[oa]|unidad|brazo)s?',
        'poste': r'(\d+)\s*(?:poste)s?',
        'cable': r'(\d+)\s*(?:metro)s?'
    }
    m = re.search(patrones[tipo], t_norm)
    return int(m.group(1)) if m else 0

# --- LOGIN ---
usuarios_db = {"SF": {"p": "1827", "r": "admin"}, "GuaDAP": {"p": "5555", "r": "consulta"}}

if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Logotipo_del_Ayuntamiento_de_Toluca.svg/1200px-Logotipo_del_Ayuntamiento_de_Toluca.svg.png", width=250)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u in usuarios_db and usuarios_db[u]["p"] == p:
                st.session_state.autenticado, st.session_state.rol, st.session_state.user = True, usuarios_db[u]["r"], u
                st.rerun()
else:
    # --- PANEL PRINCIPAL ---
    with st.sidebar:
        st.image("https://www.toluca.gob.mx/wp-content/uploads/2019/08/escudo-blanco.png", width=180)
        st.write(f"### 👤 {st.session_state.user}")
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()

    conn = st.connection("gsheets", type=GSheetsConnection)

    if st.session_state.rol == "admin":
        st.header("🛠️ Panel de Administración - SF PANGEA")
        up = st.file_uploader("Cargar Reporte de Brigada", type=["xlsx", "csv"])

        if up:
            df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
            id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
            
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            pts = df_v.to_dict('records')
            idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
            ordenados = [pts.pop(idx_lejano)]
            while pts:
                rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                ordenados.append(pts.pop(idx))

            route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
            geo_trazo, dist_real_km = get_real_route(route_coords)
            if not dist_real_km: dist_real_km = (len(ordenados) + 1) * 1.3

            for i, p in enumerate(ordenados, 1):
                p['No_Ruta'], p['ID_Pangea_Nombre'] = i, p[id_col]
                p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum')
                p['Cant_Postes'] = extraer_carga_robusta(p, 'poste')
                p['Cant_Cable_m'] = extraer_carga_robusta(p, 'cable')
                if p['Cant_Luminarias'] == 0 and p['Cant_Postes'] == 0 and p['Cant_Cable_m'] == 0: p['Cant_Luminarias'] = 1

            # MAPA VIVO
            st.subheader("📍 Visualización de Ruta Real")
            m = folium.Map(location=BASE_COORDS, zoom_start=13)
            for p in ordenados:
                folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {p['No_Ruta']}: {p['ID_Pangea_Nombre']}").add_to(m)
            if geo_trazo:
                folium.PolyLine([(c[1], c[0]) for c in geo_trazo], color="#611232", weight=5).add_to(m)
            st_folium(m, width=900, height=450)

            if st.button("💾 GUARDAR RUTA EN GOOGLE SHEETS"):
                try:
                    df_ex = conn.read()
                    nueva = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Nombre_Ruta": up.name, "Usuario": st.session_state.user, "Datos_JSON": json.dumps(ordenados)}])
                    # Eliminamos columnas vacías del existente para evitar errores de concatenación
                    df_ex = df_ex.dropna(axis=1, how='all')
                    conn.update(data=pd.concat([df_ex, nueva], ignore_index=True))
                    st.success("✅ Guardado correctamente en BD_PANGEA")
                except Exception as e: st.error(f"Error: {e}")

    # --- SECCIÓN CONSULTA / DESCARGA ---
    st.markdown("---")
    st.header("🔍 Buscador de Rutas Institucionales")
    try:
        df_bd = conn.read()
        if not df_bd.empty:
            sel = st.selectbox("Rutas en historial:", ["-- Seleccionar --"] + df_bd["Nombre_Ruta"].tolist())
            if sel != "-- Seleccionar --":
                f = df_bd[df_bd["Nombre_Ruta"] == sel].iloc[-1]
                p_rec = json.loads(f["Datos_JSON"])
                
                # Botón KML con Resumen Operativo v4.3.3
                kml = simplekml.Kml()
                capa = kml.newfolder(name="SF PANGEA")
                for p in p_rec:
                    pnt = capa.newpoint(name=str(p['ID_Pangea_Nombre']), coords=[(p['lon_aux'], p['lat_aux'])])
                    desc = f"<b>No. Ruta: {p['No_Ruta']}</b><br>Lums: {p['Cant_Luminarias']}<br>Postes: {p['Cant_Postes']}<br>Cable: {p['Cant_Cable_m']}m"
                    pnt.description = desc
                
                st.download_button("🗺️ Descargar KML", kml.kml(), f"{sel}.kml")
    except: st.info("Conectando con la base de datos...")
