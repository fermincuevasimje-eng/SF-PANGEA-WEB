import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re
import folium
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import json

# Configuración de página - Solo una vez
st.set_page_config(page_title="SF PANGEA v4.3.5", layout="wide")

# --- MOTOR DE CÁLCULO CON CACHÉ (Para evitar lentitud) ---
@st.cache_data(show_spinner=False)
def motor_pangea_pro(df_v, base_coords):
    pts = df_v.to_dict('records')
    # Vecino más cercano
    idx_lejano = np.argmax(cdist([base_coords], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
    ordenados = [pts.pop(idx_lejano)]
    while pts:
        rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
        idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
        ordenados.append(pts.pop(idx))
    return ordenados

# --- LÓGICA DE ACCESO ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🚀 SF PANGEA - SISTEMA OPERATIVO")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    # Coordenadas institucionales
    BASE_LAT_LON = (19.291395219739588, -99.63555838631413)
    
    # Conexión Segura
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except:
        st.error("Error en la conexión. Revisa los Secrets.")

    # Sidebar
    st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}))
    
    up = st.file_uploader("Subir Reporte CSV/XLSX", type=["csv", "xlsx"])

    if up:
        # 1. Carga y Limpieza (Solo una vez)
        df_raw = pd.read_excel(up) if "xlsx" in up.name else pd.read_csv(up)
        df_raw = df_raw.fillna("")
        
        # Extraer GPS
        res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
        df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
        df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
        df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

        # 2. Ejecutar Motor
        ruta_ordenada = motor_pangea_pro(df_v, BASE_LAT_LON)

        # 3. FRAGMENTO AISLADO PARA EL MAPA (Evita que parpadee al mover el mouse)
        @st.fragment
        def zona_mapa(datos_ruta):
            st.subheader("Mapa de Ruta Optimizada")
            m = folium.Map(location=BASE_LAT_LON, zoom_start=13)
            
            # Dibujar trazo de ruta
            puntos_linea = [BASE_LAT_LON] + [[p['lat_aux'], p['lon_aux']] for p in datos_ruta] + [BASE_LAT_LON]
            folium.PolyLine(puntos_linea, color="red", weight=3, opacity=0.8).add_to(m)
            
            # Marcadores
            for i, p in enumerate(datos_ruta):
                folium.Marker(
                    [p['lat_aux'], p['lon_aux']], 
                    popup=f"Punto {i+1}",
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)
                
            folium.Marker(BASE_LAT_LON, icon=folium.Icon(color="green", icon="home")).add_to(m)
            
            st_folium(m, width=900, height=500, returned_objects=[])

        zona_mapa(ruta_ordenada)

        # 4. BOTÓN DE GUARDADO
        if st.button("💾 GUARDAR EN BD_PANGEA"):
            try:
                df_ex = conn.read(ttl=0) # Leer historial actual
                nueva_fila = pd.DataFrame([{
                    "Fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                    "Reporte": up.name,
                    "Puntos": len(ruta_ordenada)
                }])
                conn.update(data=pd.concat([df_ex, nueva_fila], ignore_index=True))
                st.success("✅ Guardado exitosamente en Google Sheets.")
            except Exception as e:
                st.error(f"Error crítico al guardar: {e}")
