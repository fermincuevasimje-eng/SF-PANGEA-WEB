import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, requests, folium, json
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SF PANGEA v4.4.3", layout="wide")

# --- MOTOR DE RUTAS POR CALLES (OSRM) ---
def obtener_ruta_calles(puntos):
    if len(puntos) < 2: return puntos
    coords = ";".join([f"{lon},{lat}" for lat, lon in puntos])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=10).json()
        if 'routes' in r and len(r['routes']) > 0:
            return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except:
        pass
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

# --- CONTROL DE ACCESO (LOGIN) ---
if "autenticado" not in st.session_state: 
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🚀 SF PANGEA - ALUMBRADO PÚBLICO")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
else:
    # Coordenadas exactas solicitadas
    BASE_LAT_LON = (19.291395219739588, -99.63555838631413)
    
    # Conexión Segura
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"Error en Secrets: {e}")

    st.sidebar.title("Panel de Control")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    up = st.file_uploader("Subir Reporte (Excel o CSV)", type=["csv", "xlsx"])

    if up:
        try:
            # Lectura del archivo
            if up.name.endswith('.xlsx'):
                df_raw = pd.read_excel(up)
            else:
                df_raw = pd.read_csv(up, encoding='latin1', on_bad_lines='skip')
            
            df_raw = df_raw.fillna("")
            
            # Buscador de GPS (Regex)
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
            df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                ruta_puntos = motor_pangea_pro(df_v, BASE_LAT_LON)
                
                # --- MAPA AISLADO (Fragmento para evitar parpadeo) ---
                @st.fragment
                def zona_mapa(datos):
                    st.subheader("Mapa Operativo - Trazo por Calles (Toluca)")
                    m = folium.Map(location=BASE_LAT_LON, zoom_start=14)
                    
                    # Generar trazo real por calles
                    lista_coords = [BASE_LAT_LON] + [[p['lat_aux'], p['lon_aux']] for p in datos] + [BASE_LAT_LON]
                    trazo_real = obtener_ruta_calles(lista_coords)
                    
                    # Dibujar línea guinda institucional
                    folium.PolyLine(trazo_real, color="#611232", weight=5, opacity=0.8).add_to(m)
                    
                    for i, p in enumerate(datos):
                        folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {i+1}").add_to(m)
                    
                    folium.Marker(BASE_LAT_LON, icon=folium.Icon(color="green", icon="home")).add_to(m)
                    st_folium(m, width=1000, height=500, returned_objects=[])

                zona_mapa(ruta_puntos)

                # --- GUARDADO EN GOOGLE SHEETS (Basado en tus columnas actuales) ---
                if st.button("💾 REGISTRAR EN BITÁCORA BD_PANGEA"):
                    try:
                        # Leer historial actual de la pestaña Sheet1
                        df_historial = conn.read(worksheet="Sheet1", ttl=0)
                        
                        # Crear nueva fila con TUS columnas: Fecha, Nombre_Ruta, Usuario_Genera, Datos_JSON
                        nueva_fila = pd.DataFrame([{
                            "Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                            "Nombre_Ruta": up.name,
                            "Usuario_Genera": "SF_ADMIN",
                            "Datos_JSON": json.dumps({"puntos": len(ruta_puntos)})
                        }])
                        
                        # Concatenar y subir
                        df_final = pd.concat([df_historial, nueva_fila], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=df_final)
                        
                        st.success("✅ ¡Éxito! Ruta registrada en Google Sheets.")
                    except Exception as e:
                        st.error(f"Error al guardar. Asegúrate que la hoja se llame 'Sheet1'. Detalle: {e}")
            else:
                st.warning("No se encontraron coordenadas válidas en el archivo.")
        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")
