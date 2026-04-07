import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, requests, unicodedata, simplekml, io, json
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SF PANGEA v4.5.3", layout="wide")

BASE_COORDS = (19.291395219739588, -99.63555838631413)
URL_HOJA = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzeJSbMwxUm8/edit#gid=0"
NOMBRE_HOJA = "Sheet1" 

# --- FUNCIONES LÓGICAS ---
def normalizar(t):
    return "".join(c for c in unicodedata.normalize('NFD', str(t)) if unicodedata.category(c) != 'Mn').lower()

def extraer_carga(p_dict, tipo):
    d = {'un ':'1 ','uno ':'1 ','una ':'1 ','dos ':'2 ','tres ':'3 ','cuatro ':'4 ','cinco ':'5 '}
    txt = ""
    for c in ['ASUNTO', 'Observaciones', 'asunto', 'Asunto']:
        if c in p_dict and str(p_dict[c]).strip():
            txt = str(p_dict[c]); break
    t_n = normalizar(txt)
    for p, v in d.items(): t_n = t_n.replace(p, v)
    pats = {'lum': r'(\d+)\s*(?:lampara|foco|reflector|luminari|unidad)', 'poste': r'(\d+)\s*(?:poste)', 'cable': r'(\d+)\s*(?:metro)'}
    m = re.search(pats.get(tipo, ''), t_n)
    return int(m.group(1)) if m else 0

# --- INTERFAZ ---
st.title("🚀 SF PANGEA - Gestión de Rutas Toluca")

tab1, tab2 = st.tabs(["🆕 Generar Productos", "📂 Historial y My Maps"])

with tab1:
    up = st.file_uploader("Subir Reporte (Excel/CSV)", type=["csv", "xlsx"])
    if up:
        try:
            df_raw = pd.read_excel(up) if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin1')
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
            df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                # LÓGICA DE RUTA: Punto 1 = El más lejano
                pts = df_v.to_dict('records')
                coords_array = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                idx_lejano = np.argmax(cdist([BASE_COORDS], coords_array)[0])
                
                ordenados = [pts.pop(idx_lejano)]
                while pts:
                    rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                    idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                    ordenados.append(pts.pop(idx))

                df_f = pd.DataFrame(ordenados)
                for i, r in df_f.iterrows():
                    df_f.at[i, 'No_Ruta'] = i + 1
                    df_f.at[i, 'Cant_Luminarias'] = extraer_carga(r, 'lum') or 1
                    df_f.at[i, 'ID_Pangea'] = r.get('FOLIO', r.get('ID', 'S/N'))

                st.success(f"✅ Optimizada: {len(df_f)} puntos. Inicio en el punto más lejano.")

                # CONTENEDOR DE DESCARGAS
                with st.container(border=True):
                    st.write("### ⬇️ Descargar Archivos para My Maps")
                    c1, c2, c3 = st.columns(3)
                    
                    # CORRECCIÓN KML: simplekml.Kml() con minúsculas
                    kml_obj = simplekml.Kml()
                    for _, p in df_f.iterrows():
                        kml_obj.newpoint(name=f"{int(p['No_Ruta'])}-{p['ID_Pangea']}", coords=[(p['lon_aux'], p['lat_aux'])])
                    
                    c1.download_button("📥 KML", kml_obj.kml(), file_name=f"{up.name}.kml", use_container_width=True)
                    c2.download_button("📊 CSV", df_f.to_csv(index=False).encode('utf-8-sig'), file_name=f"{up.name}.csv", use_container_width=True)
                    
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as w: df_f.to_excel(w, index=False)
                    c3.download_button("📗 Excel", buf.getvalue(), file_name=f"{up.name}.xlsx", use_container_width=True)

                if st.button("💾 Guardar en Bitácora Virtual"):
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        hist = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
                        nueva = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y"), "Nombre_Ruta": up.name, "Usuario_Genera": "ADMIN_PANGEA", "Datos_JSON": f"{len(df_f)} pts"}])
                        conn.update(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, data=pd.concat([hist, nueva], ignore_index=True))
                        st.success(f"Guardado correctamente en {NOMBRE_HOJA}")
                    except Exception as e: st.error(f"Error de conexión: {e}")
            else:
                st.warning("No se detectaron coordenadas GPS en el archivo.")
        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")

with tab2:
    st.subheader("📂 Repositorio de Rutas Generadas")
    # URL de My Maps corregida
    st.link_button("🗺️ ABRIR GOOGLE MY MAPS", "https://www.google.com/maps/d/", type="primary")
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        historial = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
        busqueda = st.text_input("🔍 Buscar por nombre o fecha...")
        if busqueda:
            historial = historial[historial.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]
        st.dataframe(historial, use_container_width=True)
    except:
        st.info("Conexión con Google Sheets pendiente o tabla vacía.")
