import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, requests, folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="SF PANGEA v4.4.0", layout="wide")

# --- FUNCIÓN PARA TRAZAR POR CALLES (OSRM GRATUITO) ---
def obtener_ruta_calles(puntos):
    # OSRM solo aguanta grupos de puntos, así que los unimos
    coords = ";".join([f"{lon},{lat}" for lat, lon in puntos])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
    try:
        r = requests.get(url).json()
        return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except:
        return puntos # Si falla el servidor, vuelve a línea recta

@st.cache_data(show_spinner=False)
def motor_pangea_pro(df_v, base_coords):
    pts = df_v.to_dict('records')
    idx_lejano = np.argmax(cdist([base_coords], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
    ordenados = [pts.pop(idx_lejano)]
    while pts:
        rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
        idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
        ordenados.append(pts.pop(idx))
    return ordenados

# --- LÓGICA ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🚀 SF PANGEA - SISTEMA OPERATIVO")
    u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    BASE_LAT_LON = (19.291395219739588, -99.63555838631413)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    up = st.file_uploader("Subir Reporte CSV/XLSX", type=["csv", "xlsx"])

    if up:
        # Carga reforzada
        df_raw = pd.read_excel(up) if "xlsx" in up.name else pd.read_csv(up, encoding='latin1', errors='replace')
        df_raw = df_raw.fillna("")
        res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
        df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
        df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
        df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

        if not df_v.empty:
            ruta_puntos = motor_pangea_pro(df_v, BASE_LAT_LON)
            
            @st.fragment
            def vista_mapa():
                st.subheader("Mapa con Sentido de Calles (OSRM)")
                m = folium.Map(location=BASE_LAT_LON, zoom_start=13)
                
                # Obtener trazo real por calles
                puntos_para_osrm = [BASE_LAT_LON] + [[p['lat_aux'], p['lon_aux']] for p in ruta_puntos] + [BASE_LAT_LON]
                geometria_real = obtener_ruta_calles(puntos_para_osrm)
                
                folium.PolyLine(geometria_real, color="#611232", weight=5).add_to(m)
                for i, p in enumerate(ruta_puntos):
                    folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {i+1}").add_to(m)
                folium.Marker(BASE_LAT_LON, icon=folium.Icon(color="green", icon="home")).add_to(m)
                st_folium(m, width=1000, height=500, returned_objects=[])

            vista_mapa()

            if st.button("💾 GUARDAR EN BD_PANGEA"):
                try:
                    df_ex = conn.read(ttl=0)
                    nueva = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Reporte": up.name, "Puntos": len(ruta_puntos)}])
                    conn.update(data=pd.concat([df_ex, nueva], ignore_index=True))
                    st.success("✅ Guardado exitosamente.")
                except Exception as e:
                    st.error(f"Error de permisos: Asegúrate de que el JSON en Secrets sea exacto y el Excel sea compartido.")
