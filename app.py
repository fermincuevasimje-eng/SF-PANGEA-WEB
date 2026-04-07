import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SF PANGEA v4.5.6", layout="wide")

# Coordenadas de la Base (Toluca)
BASE_COORDS = (19.291395219739588, -99.63555838631413)
URL_HOJA = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzeJSbMwxUm8/edit#gid=0"
NOMBRE_HOJA = "Sheet1"

# --- FUNCIONES DE APOYO ---
def normalizar(t):
    return "".join(c for c in unicodedata.normalize('NFD', str(t)) if unicodedata.category(c) != 'Mn').lower()

def extraer_carga(p_dict):
    txt = ""
    # Intentar obtener texto de columnas comunes
    for c in ['ASUNTO', 'Observaciones', 'asunto', 'Asunto', 'OBSERVACIONES']:
        if c in p_dict and str(p_dict[c]).strip():
            txt = str(p_dict[c])
            break
    t_n = normalizar(txt)
    # Buscar números seguidos de palabras clave
    m = re.search(r'(\d+)\s*(?:lampara|foco|reflector|luminari|unidad|brazo)', t_n)
    return int(m.group(1)) if m else 1

# --- LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso SF PANGEA")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
else:
    # --- APP PRINCIPAL ---
    st.title("🚀 SF PANGEA - Alumbrado Público")
    st.sidebar.success(f"Conectado como: SF")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

    tab1, tab2 = st.tabs(["🆕 Generar Ruta", "📂 Historial y Bitácora"])

    with tab1:
        up = st.file_uploader("Subir Reporte (Excel o CSV)", type=["csv", "xlsx"])
        
        if up:
            try:
                # 1. LECTURA Y LIMPIEZA DE NULOS (Evita el TypeError)
                if up.name.endswith('.xlsx'):
                    df_raw = pd.read_excel(up).fillna("")
                else:
                    df_raw = pd.read_csv(up, encoding='latin1').fillna("")
                
                # 2. BÚSQUEDA DE GPS EN TODO EL TEXTO
                # Convertimos todo a string y unimos para que el Regex encuentre las coordenadas
                res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                
                df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
                df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
                
                # Filtrar solo filas con GPS
                df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

                if not df_v.empty:
                    # 3. LÓGICA DE RUTA: EL PUNTO 1 ES EL MÁS LEJANO A LA BASE
                    pts = df_v.to_dict('records')
                    coords_arr = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                    
                    # Calcular distancias a la base y tomar el máximo
                    distancias_base = cdist([BASE_COORDS], coords_arr)[0]
                    idx_lejano = np.argmax(distancias_base)
                    
                    ordenados = [pts.pop(idx_lejano)]
                    
                    # Vecino más cercano desde el punto lejano
                    while pts:
                        actual = np.array([[ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux']]])
                        restantes = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                        idx_proximo = np.argmin(cdist(actual, restantes))
                        ordenados.append(pts.pop(idx_proximo))

                    df_f = pd.DataFrame(ordenados)
                    df_f['No_Ruta'] = range(1, len(df_f) + 1)
                    df_f['Cant_Lum'] = df_f.apply(extraer_carga, axis=1)
                    
                    # Mostrar resumen
                    st.success(f"✅ Se identificaron {len(df_f)} puntos. La ruta inicia en el punto más lejano a la base.")
                    
                    # 4. BOTONES DE DESCARGA
                    with st.container(border=True):
                        st.write("### ⬇️ Descargar Archivos")
                        c1, c2, c3 = st.columns(3)
                        
                        # Generar KML
                        kml = simplekml.Kml()
                        for _, r in df_f.iterrows():
                            kml.newpoint(name=f"P{int(r['No_Ruta'])}", coords=[(r['lon_aux'], r['lat_aux'])])
                        
                        c1.download_button("📥 KML (My Maps)", kml.kml(), file_name=f"{up.name}.kml", use_container_width=True)
                        c2.download_button("📊 CSV", df_f.to_csv(index=False).encode('utf-8-sig'), file_name=f"{up.name}.csv", use_container_width=True)
                        
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='openpyxl') as w:
                            df_f.to_excel(w, index=False)
                        c3.download_button("📗 Excel", buf.getvalue(), file_name=f"{up.name}.xlsx", use_container_width=True)

                    # 5. GUARDADO EN GOOGLE SHEETS
                    if st.button("💾 REGISTRAR EN BITÁCORA"):
                        try:
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            hist = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
                            nueva_fila = pd.DataFrame([{
                                "Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                                "Nombre_Ruta": up.name,
                                "Usuario_Genera": "SF_ADMIN",
                                "Datos_JSON": f"{len(df_f)} puntos"
                            }])
                            conn.update(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, data=pd.concat([hist, nueva_fila], ignore_index=True))
                            st.balloons()
                            st.success("¡Datos sincronizados con Google Sheets!")
                        except Exception as e:
                            st.error(f"Error al conectar con la bitácora: {e}")
                else:
                    st.warning("⚠️ El archivo no contiene coordenadas GPS válidas (formato: lat, lon).")
            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")

    with tab2:
        st.subheader("📂 Bitácora de Rutas Generadas")
        st.link_button("🗺️ Abrir Google My Maps", "https://www.google.com/maps/d/u/0/create", type="primary")
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_hist = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
            
            filtro = st.text_input("🔍 Buscar por nombre de ruta...")
            if filtro:
                df_hist = df_hist[df_hist['Nombre_Ruta'].str.contains(filtro, case=False)]
            
            st.dataframe(df_hist.sort_index(ascending=False), use_container_width=True)
        except:
            st.info("Cargando bitácora...")
