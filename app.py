import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, requests, folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="SF PANGEA v4.4.1", layout="wide")

# --- TRAZO POR CALLES REALES (OSRM) ---
def obtener_ruta_calles(puntos):
    if len(puntos) < 2: return puntos
    coords = ";".join([f"{lon},{lat}" for lat, lon in puntos])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10).json()
        if 'routes' in r:
            return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except:
        pass
    return puntos

@st.cache_data(show_spinner=False)
def motor_pangea_pro(df_v, base_coords):
    pts = df_v.to_dict('records')
    # Lógica de optimización de ruta
    coords_array = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
    idx_lejano = np.argmax(cdist([base_coords], coords_array)[0])
    ordenados = [pts.pop(idx_lejano)]
    while pts:
        rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
        idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
        ordenados.append(pts.pop(idx))
    return ordenados

# --- INICIO DE APP ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🚀 SF PANGEA - DIRECCIÓN DE ALUMBRADO")
    u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    BASE_LAT_LON = (19.291395219739588, -99.63555838631413)
    
    # Intentar conexión con Google Sheets
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"Error de conexión: Verifica los Secrets. {e}")

    up = st.file_uploader("Subir Reporte CSV/XLSX", type=["csv", "xlsx"])

    if up:
        # Carga inteligente de archivos
        try:
            if up.name.endswith('.xlsx'):
                df_raw = pd.read_excel(up)
            else:
                df_raw = pd.read_csv(up, encoding='latin1', on_bad_lines='skip')
            
            df_raw = df_raw.fillna("")
            # Extraer GPS con Regex
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
            df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                ruta_puntos = motor_pangea_pro(df_v, BASE_LAT_LON)
                
                @st.fragment
                def zona_mapa():
                    st.subheader("Mapa de Ruta Institucional (Calles Reales)")
                    m = folium.Map(location=BASE_LAT_LON, zoom_start=13)
                    
                    # Dibujar ruta siguiendo calles
                    lista_coords = [BASE_LAT_LON] + [[p['lat_aux'], p['lon_aux']] for p in ruta_puntos] + [BASE_LAT_LON]
                    trazo_real = obtener_ruta_calles(lista_coords)
                    
                    folium.PolyLine(trazo_real, color="#611232", weight=5, opacity=0.8).add_to(m)
                    
                    for i, p in enumerate(ruta_puntos):
                        folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {i+1}").add_to(m)
                    
                    folium.Marker(BASE_LAT_LON, icon=folium.Icon(color="green", icon="home")).add_to(m)
                    st_folium(m, width=1000, height=500, returned_objects=[])

                zona_mapa()

                # Botón de Guardado
                if st.button("💾 REGISTRAR EN BITÁCORA BD_PANGEA"):
                    try:
                        # Leer datos actuales para concatenar
                        df_historial = conn.read(ttl=0)
                        nueva_fila = pd.DataFrame([{
                            "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                            "Archivo": up.name,
                            "Total_Puntos": len(ruta_puntos)
                        }])
                        df_final = pd.concat([df_historial, nueva_fila], ignore_index=True)
                        conn.update(data=df_final)
                        st.success("✅ Datos guardados correctamente en la Nube.")
                    except Exception as e:
                        st.error(f"No se pudo guardar: Revisa los permisos del Excel. {e}")
            else:
                st.warning("No se detectaron coordenadas GPS válidas en el archivo.")
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
