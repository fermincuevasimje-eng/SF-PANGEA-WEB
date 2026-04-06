import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, requests, folium, json
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SF PANGEA v4.4.4", layout="wide")

# --- MOTOR DE RUTAS POR CALLES ---
def obtener_ruta_calles(puntos):
    if len(puntos) < 2: return puntos
    coords = ";".join([f"{lon},{lat}" for lat, lon in puntos])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10).json()
        if 'routes' in r and len(r['routes']) > 0:
            return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except: pass
    return puntos

@st.cache_data(show_spinner=False)
def motor_pangea_pro(df_v, base_coords):
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
    st.title("🚀 SF PANGEA - ALUMBRADO PÚBLICO")
    u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    BASE_LAT_LON = (19.291395219739588, -99.63555838631413)
    URL_EXCEL = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzeJSbMwxUm8/edit#gid=0"

    try:
        # Conexión forzada a la URL de tu captura
        conn = st.connection("gsheets", type=GSheetsConnection)
    except:
        st.error("Error en configuración de Secrets.")

    up = st.file_uploader("Subir Reporte (Excel o CSV)", type=["csv", "xlsx"])

    if up:
        try:
            df_raw = pd.read_excel(up) if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin1')
            df_raw = df_raw.fillna("")
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
            df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                ruta_puntos = motor_pangea_pro(df_v, BASE_LAT_LON)
                
                @st.fragment
                def zona_mapa(datos):
                    st.subheader("Mapa Operativo - Trazo por Calles")
                    m = folium.Map(location=BASE_LAT_LON, zoom_start=14)
                    lista_coords = [BASE_LAT_LON] + [[p['lat_aux'], p['lon_aux']] for p in datos] + [BASE_LAT_LON]
                    trazo = obtener_ruta_calles(lista_coords)
                    folium.PolyLine(trazo, color="#611232", weight=5, opacity=0.8).add_to(m)
                    for i, p in enumerate(datos):
                        folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {i+1}").add_to(m)
                    folium.Marker(BASE_LAT_LON, icon=folium.Icon(color="green", icon="home")).add_to(m)
                    st_folium(m, width=1000, height=500)

                zona_mapa(ruta_puntos)

                # --- GUARDADO AUTOMÁTICO (CORREGIDO) ---
                if st.button("💾 REGISTRAR EN BITÁCORA BD_PANGEA"):
                    try:
                        # Leemos usando la URL directa para evitar el 404
                        df_historial = conn.read(spreadsheet=URL_EXCEL, ttl=0)
                        
                        nueva_fila = pd.DataFrame([{
                            "Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                            "Nombre_Ruta": up.name,
                            "Usuario_Genera": "SF_ADMIN",
                            "Datos_JSON": json.dumps({"puntos": len(ruta_puntos)})
                        }])
                        
                        df_final = pd.concat([df_historial, nueva_fila], ignore_index=True)
                        
                        # Actualización forzada
                        conn.update(spreadsheet=URL_EXCEL, data=df_final)
                        st.success("✅ ¡Ruta guardada correctamente!")
                    except Exception as e:
                        st.error(f"Error crítico al guardar: {e}")
            else:
                st.warning("No se detectaron coordenadas.")
        except Exception as e:
            st.error(f"Error de archivo: {e}")
