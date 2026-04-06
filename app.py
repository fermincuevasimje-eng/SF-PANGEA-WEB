import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import json

st.set_page_config(page_title="SF PANGEA v4.3.6", layout="wide")

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

if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🚀 SF PANGEA - Acceso")
    u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    BASE_LAT_LON = (19.291395219739588, -99.63555838631413)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}))
    up = st.file_uploader("Subir Reporte CSV/XLSX", type=["csv", "xlsx"])

    if up:
        # --- CARGA SEGURA DE DATOS ---
        if "xlsx" in up.name:
            df_raw = pd.read_excel(up).fillna("")
        else:
            try:
                df_raw = pd.read_csv(up, encoding='latin1').fillna("")
            except:
                df_raw = pd.read_csv(up, encoding='utf-8', errors='replace').fillna("")
        
        # Extraer GPS
        res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
        df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
        df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
        df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

        if not df_v.empty:
            ruta_ordenada = motor_pangea_pro(df_v, BASE_LAT_LON)

            # --- MAPA QUE NO PARPADEA ---
            @st.fragment
            def zona_mapa(datos_ruta):
                m = folium.Map(location=BASE_LAT_LON, zoom_start=13)
                # Trazo de ruta (Línea Roja)
                puntos_linea = [BASE_LAT_LON] + [[p['lat_aux'], p['lon_aux']] for p in datos_ruta] + [BASE_LAT_LON]
                folium.PolyLine(puntos_linea, color="#611232", weight=4, opacity=0.8).add_to(m)
                
                # Marcadores
                for i, p in enumerate(datos_ruta):
                    folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {i+1}").add_to(m)
                folium.Marker(BASE_LAT_LON, icon=folium.Icon(color="green", icon="home")).add_to(m)
                
                st_folium(m, width=1000, height=500, returned_objects=[])

            zona_mapa(ruta_ordenada)

            if st.button("💾 GUARDAR EN BD_PANGEA"):
                try:
                    df_ex = conn.read(ttl=0)
                    nueva = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Reporte": up.name, "Puntos": len(ruta_ordenada)}])
                    conn.update(data=pd.concat([df_ex, nueva], ignore_index=True))
                    st.success("✅ Guardado exitosamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
        else:
            st.warning("No se encontraron coordenadas válidas en el archivo.")
