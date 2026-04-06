import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import simplekml
import re
import unicodedata
import requests
import io
from openpyxl.styles import PatternFill

# ==========================================================
# SF PANGEA v4.3.3 - MULTI-USER & HISTORY EDITION
# ==========================================================

st.set_page_config(page_title="SF PANGEA", page_icon="🚀", layout="wide")

# --- BASE DE DATOS DE USUARIOS ---
usuarios_db = {
    "SF": {"password": "1827", "rol": "admin"},
    "GuaDAP": {"password": "5555", "rol": "consulta"}
}

# Inicializar historial en la memoria del servidor si no existe
if "historial_rutas" not in st.session_state:
    st.session_state.historial_rutas = {}

def login_seccion():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.rol = None
        st.session_state.user = None

    if not st.session_state.autenticado:
        st.title("🔐 Acceso SF PANGEA")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
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
    st.sidebar.title(f"👤 {st.session_state.user}")
    st.sidebar.info(f"Permisos: {st.session_state.rol.upper()}")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    t_unidad_min = st.sidebar.number_input("Minutos por Punto", value=20)
    v_ciu = st.sidebar.number_input("Velocidad Promedio (km/h)", value=25)
    BASE_COORDS = (19.291395219739588, -99.63555838631413)

    # --- FUNCIONES CORE ---
    def get_real_route(coords_list):
        locs = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
        url = f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson"
        try:
            r = requests.get(url).json()
            return r['routes'][0]['geometry']['coordinates'], r['routes'][0]['distance'] / 1000
        except: return None, None

    def extraer_carga_robusta(punto_dict, tipo):
        d_letras = {'un ':'1 ','uno ':'1 ','una ':'1 ','dos ':'2 ','tres ':'3 ','cuatro ':'4 '}
        texto_fuente = str(punto_dict.get('ASUNTO', '')) + " " + str(punto_dict.get('Observaciones', ''))
        t_norm = "".join(c for c in unicodedata.normalize('NFD', texto_fuente.lower()) if unicodedata.category(c) != 'Mn')
        for p, n in d_letras.items(): t_norm = t_norm.replace(p, n)
        patrones = {'lum': r'(\d+)\s*(?:lampara|foco|luminari)', 'poste': r'(\d+)\s*(?:poste)', 'cable': r'(\d+)\s*(?:metro)'}
        m = re.search(patrones.get(tipo, ''), t_norm)
        return int(m.group(1)) if m else 0

    # --- LÓGICA POR ROL ---
    
    if st.session_state.rol == "admin":
        st.header("🛠️ Panel de Administración (Generador de Rutas)")
        uploaded_file = st.file_uploader("Sube el archivo de brigada", type=["xlsx", "csv"])

        if uploaded_file:
            with st.spinner("Procesando SF PANGEA..."):
                df = pd.read_excel(uploaded_file, dtype=str).fillna("") if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file, encoding='latin-1', dtype=str).fillna("")
                res_gps = df.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                df['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
                df['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
                df_v = df.dropna(subset=['lat_aux']).reset_index(drop=True)

                if not df_v.empty:
                    pts = df_v.to_dict('records')
                    # Optimización simple
                    idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
                    ordenados = [pts.pop(idx_lejano)]
                    while pts:
                        rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                        idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                        ordenados.append(pts.pop(idx))

                    # Guardar en Historial para GuaDAP
                    nombre_ruta = f"Ruta_{uploaded_file.name}_{pd.Timestamp.now().strftime('%H:%M')}"
                    st.session_state.historial_rutas[nombre_ruta] = ordenados
                    st.success(f"✅ Ruta '{nombre_ruta}' generada y disponible para consulta.")

                    # Métricas Rápidas
                    tl = sum(extraer_carga_robusta(x, 'lum') or 1 for x in ordenados)
                    st.metric("Total Luminarias en esta ruta", tl)

    # --- SECCIÓN DE CONSULTA (PARA AMBOS) ---
    st.markdown("---")
    st.header("🔍 Buscador de Rutas Generadas")
    
    if st.session_state.historial_rutas:
        opciones = list(st.session_state.historial_rutas.keys())
        seleccion = st.selectbox("Selecciona una ruta para consultar:", ["-- Seleccionar --"] + opciones)

        if seleccion != "-- Seleccionar --":
            datos_ruta = st.session_state.historial_rutas[seleccion]
            df_mostrar = pd.DataFrame(datos_ruta)
            
            st.write(f"Mostrando datos de: **{seleccion}**")
            st.dataframe(df_mostrar[['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias'] if 'No_Ruta' in df_mostrar.columns else df_mostrar.columns[:5]])

            # Botones de descarga habilitados para todos
            kml = simplekml.Kml()
            for p in datos_ruta:
                kml.newpoint(name=str(p.get('ID_Pangea_Nombre', 'Punto')), coords=[(p['lon_aux'], p['lat_aux'])])
            
            st.download_button(f"🗺️ Descargar KML de {seleccion}", kml.kml(), f"{seleccion}.kml")
    else:
        st.warning("No hay rutas procesadas en esta sesión todavía.")
