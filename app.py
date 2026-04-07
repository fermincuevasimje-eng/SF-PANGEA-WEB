import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="SF PANGEA v4.5.5", layout="wide")

BASE_COORDS = (19.291395219739588, -99.63555838631413)
URL_HOJA = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzeJSbMwxUm8/edit#gid=0"
NOMBRE_HOJA = "Sheet1"

def normalizar(t):
    return "".join(c for c in unicodedata.normalize('NFD', str(t)) if unicodedata.category(c) != 'Mn').lower()

def extraer_carga(p_dict):
    txt = ""
    for c in ['ASUNTO', 'Observaciones', 'asunto', 'Asunto']:
        if c in p_dict and str(p_dict[c]).strip():
            txt = str(p_dict[c]); break
    t_n = normalizar(txt)
    m = re.search(r'(\d+)\s*(?:lampara|foco|reflector|luminari|unidad)', t_n)
    return int(m.group(1)) if m else 1

# --- INTERFAZ ---
st.title("🚀 SF PANGEA - Dirección de Alumbrado")

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"autenticado": False}))
    tab1, tab2 = st.tabs(["🆕 Generar Ruta", "📂 Historial de Bitácora"])

    with tab1:
        up = st.file_uploader("Subir Excel/CSV de Reportes", type=["csv", "xlsx"])
        if up:
            df_raw = pd.read_excel(up) if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin1')
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
            df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                # LÓGICA DE RUTA (Punto 1 más lejano de la base)
                pts = df_v.to_dict('records')
                coords_arr = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                idx_lejano = np.argmax(cdist([BASE_COORDS], coords_arr)[0])
                
                ordenados = [pts.pop(idx_lejano)]
                while pts:
                    actual = np.array([[ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux']]])
                    restantes = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                    idx_proximo = np.argmin(cdist(actual, restantes))
                    ordenados.append(pts.pop(idx_proximo))

                df_f = pd.DataFrame(ordenados)
                df_f['No_Ruta'] = range(1, len(df_f) + 1)
                df_f['Cant'] = df_f.apply(extraer_carga, axis=1)

                st.success(f"Ruta generada: {len(df_f)} puntos identificados.")

                # DESCARGAS
                c1, c2, c3 = st.columns(3)
                kml = simplekml.Kml()
                for _, r in df_f.iterrows():
                    kml.newpoint(name=f"R{int(r['No_Ruta'])}", coords=[(r['lon_aux'], r['lat_aux'])])
                
                c1.download_button("📥 Descargar KML", kml.kml(), file_name="ruta.kml")
                c2.download_button("📊 Descargar CSV", df_f.to_csv(index=False).encode('utf-8-sig'), file_name="ruta.csv")
                
                if st.button("💾 REGISTRAR EN GOOGLE SHEETS"):
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        hist = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
                        nueva = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Nombre_Ruta": up.name, "Puntos": len(df_f)}])
                        conn.update(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, data=pd.concat([hist, nueva], ignore_index=True))
                        st.balloons()
                        st.success("Guardado exitoso en la nube.")
                    except Exception as e: st.error(f"Error: {e}")
            else: st.warning("No hay GPS en el archivo.")

    with tab2:
        st.subheader("Bitácora de Trabajo")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            st.dataframe(conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0), use_container_width=True)
        except: st.info("Conectando con la base de datos...")
