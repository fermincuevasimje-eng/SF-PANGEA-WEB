import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, requests, folium, json
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="SF PANGEA v4.4.5", layout="wide")

# --- MOTOR DE RUTAS POR CALLES CON CACHÉ (Evita pausas) ---
@st.cache_data(show_spinner=True) # <-- CLAVE 1: Congela el cálculo para que no se repita
def obtener_ruta_calles_real(puntos_ordenados, base_coords):
    if len(puntos_ordenados) < 2: return puntos_ordenados
    
    # Prepara puntos incluyendo base al inicio y final
    todos_puntos = [base_coords] + [[p['lat_aux'], p['lon_aux']] for p in puntos_ordenados] + [base_coords]
    
    # Cadena de coordenadas para OSRM
    coords_str = ";".join([f"{lon},{lat}" for lat, lon in todos_puntos])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    
    try:
        r = requests.get(url, timeout=15).json()
        if 'routes' in r and len(r['routes']) > 0:
            # Extrae geometría real
            return [(p[1], p[0]) for p in r['routes'][0]['geometry']['coordinates']]
    except Exception as e:
        st.error(f"Error consultando servidor de calles: {e}")
        pass
    
    return todos_puntos # Retorno seguro en línea recta

@st.cache_data(show_spinner=False)
def motor_optimizador(df_v, base_coords):
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
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🚀 SF PANGEA - SISTEMA OPERATIVO")
    u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    # --- CONFIGURACIÓN DE NUBE ---
    BASE_LAT_LON = (19.291395219739588, -99.63555838631413)
    # URL directa de tu Excel para evitar el 404
    URL_GSHEET = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzeJSbMwxUm8/edit#gid=0"
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except:
        st.error("Error en Secrets.")

    st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}))
    
    up = st.file_uploader("Subir Reporte (Excel o CSV)", type=["csv", "xlsx"])

    if up:
        try:
            # Lectura del archivo
            df_raw = pd.read_excel(up) if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin1', on_bad_lines='skip')
            df_raw = df_raw.fillna("")
            
            # Buscador de coordenadas GPS
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
            df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                # 1. Optimizar orden
                puntos_ordenados = motor_optimizador(df_v, BASE_LAT_LON)
                
                # 2. Obtener trazo real por calles (UNA SOLA VEZ gracias al Caché)
                trazo_real_calles = obtener_ruta_calles_real(puntos_ordenados, BASE_LAT_LON)
                
                # --- FRAGMENTO DE MAPA AISLADO (Estabilidad Total) ---
                @st.fragment
                def zona_mapa_estable(geometria, puntos):
                    st.subheader("Mapa Operativo Toluca - Trazo por Calles Real")
                    m = folium.Map(location=BASE_LAT_LON, zoom_start=14)
                    
                    # Dibujar trazo real guinda
                    folium.PolyLine(geometria, color="#611232", weight=5, opacity=0.85).add_to(m)
                    
                    # Marcadores
                    for i, p in enumerate(puntos):
                        folium.Marker([p['lat_aux'], p['lon_aux']], popup=f"Punto {i+1}").add_to(m)
                    folium.Marker(BASE_LAT_LON, icon=folium.Icon(color="green", icon="home")).add_to(m)
                    
                    st_folium(m, width=1000, height=500, returned_objects=[])

                # Llamamos a la zona del mapa
                zona_mapa_estable(trazo_real_calles, puntos_ordenados)

                # --- GUARDADO EN GOOGLE SHEETS (USANDO TU URL DIRECTA) ---
                if st.button("💾 REGISTRAR EN BITÁCORA BD_PANGEA"):
                    try:
                        # Leer historial usando la URL forzada
                        df_historial = conn.read(spreadsheet=URL_GSHEET, worksheet="Sheet1", ttl=0)
                        
                        nueva_fila = pd.DataFrame([{
                            "Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                            "Nombre_Ruta": up.name,
                            "Usuario_Genera": "SF_OPERADOR",
                            "Datos_JSON": json.dumps({"puntos": len(puntos_ordenados)})
                        }])
                        
                        df_final = pd.concat([df_historial, nueva_fila], ignore_index=True)
                        
                        # Guardar usando la URL forzada
                        conn.update(spreadsheet=URL_GSHEET, worksheet="Sheet1", data=df_final)
                        st.success("✅ Ruta registrada exitosamente en Google Sheets.")
                    except Exception as e:
                        st.error(f"Error al escribir en la nube. Revisa permisos o si la hoja se llama 'Sheet1'. {e}")
            else:
                st.warning("No se encontraron coordenadas GPS válidas.")
        except Exception as e:
            st.error(f"Error procesando archivo: {e}")
