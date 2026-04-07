import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, requests, folium, json
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SF PANGEA v4.4.6", layout="wide")

# --- MOTOR DE RUTAS ESTABLE (CACHÉ) ---
@st.cache_data(show_spinner=True)
def calcular_geometria_calles(puntos_ordenados, base_coords):
    """Calcula el trazo real por calles una sola vez."""
    if len(puntos_ordenados) < 2: return puntos_ordenados
    todos = [base_coords] + [[p['lat_aux'], p['lon_aux']] for p in puntos_ordenados] + [base_coords]
    coords_str = ";".join([f"{lon},{lat}" for lat, lon in todos])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=15).json()
        if 'routes' in r:
            return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: pass
    return todos

@st.cache_data(show_spinner=False)
def optimizar_orden_puntos(df_v, base_coords):
    """Ordena los puntos por cercanía."""
    pts = df_v.to_dict('records')
    coords_array = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
    idx_lejano = np.argmax(cdist([base_coords], coords_array)[0])
    ordenados = [pts.pop(idx_lejano)]
    while pts:
        rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
        idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
        ordenados.append(pts.pop(idx))
    return ordenados

# --- LOGIN ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🚀 SF PANGEA - DIRECCIÓN DE ALUMBRADO")
    u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    BASE_COORD = (19.291395219739588, -99.63555838631413)
    # URL de tu archivo BD_PANGEA (extraída de tu captura)
    URL_HOJA = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzeJSbMwxUm8/edit#gid=0"

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except: pass

    st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}))
    up = st.file_uploader("Subir Reporte CSV/XLSX", type=["csv", "xlsx"])

    if up:
        try:
            df_raw = pd.read_excel(up) if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin1', on_bad_lines='skip')
            df_raw = df_raw.fillna("")
            
            # Buscador de GPS
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
            df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                # 1. Optimizar y Trazar (Con Caché para evitar pausas)
                puntos_ruta = optimizar_orden_puntos(df_v, BASE_COORD)
                trazo_calles = calcular_geometria_calles(puntos_ruta, BASE_COORD)
                
                # --- MAPA ESTABLE ---
                @st.fragment
                def mostrar_mapa(geometria, marcas):
                    st.subheader("Mapa Operativo - Trazo Real por Calles")
                    m = folium.Map(location=BASE_COORD, zoom_start=14)
                    folium.PolyLine(geometria, color="#611232", weight=5, opacity=0.8).add_to(m)
                    for i, p in enumerate(marcas):
                        folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {i+1}").add_to(m)
                    folium.Marker(BASE_COORD, icon=folium.Icon(color="green", icon="home")).add_to(m)
                    st_folium(m, width=1000, height=500, returned_objects=[])

                mostrar_mapa(trazo_calles, puntos_ruta)

                # --- LÓGICA DE GUARDADO FINAL (SIN ERROR 404) ---
                if st.button("💾 REGISTRAR EN BITÁCORA BD_PANGEA"):
                    with st.spinner("Conectando con la base de datos..."):
                        try:
                            # Intentamos leer la hoja específica 'Sheet1'
                            df_historial = conn.read(spreadsheet=URL_HOJA, worksheet="Sheet1", ttl=0)
                            
                            nueva_fila = pd.DataFrame([{
                                "Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                                "Nombre_Ruta": up.name,
                                "Usuario_Genera": "OPERADOR_SF",
                                "Datos_JSON": f"Puntos: {len(puntos_ruta)}"
                            }])
                            
                            df_final = pd.concat([df_historial, nueva_fila], ignore_index=True)
                            
                            # Actualizar usando la URL y hoja exacta
                            conn.update(spreadsheet=URL_HOJA, worksheet="Sheet1", data=df_final)
                            st.success("✅ ¡Registro exitoso en BD_PANGEA!")
                        except Exception as e:
                            st.error(f"Error de conexión. Asegúrate que en Google Sheets la pestaña se llame 'Sheet1' (con S mayúscula).")
                            st.info("Detalle técnico: Si el error persiste, verifica que el archivo sea público para 'Cualquier persona con el enlace'.")
            else:
                st.warning("No se encontraron coordenadas válidas.")
        except Exception as e:
            st.error(f"Error procesando archivo: {e}")
