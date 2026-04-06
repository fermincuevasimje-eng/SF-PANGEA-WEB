import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import simplekml
import re
import unicodedata
import requests
import time
import io
from openpyxl.styles import PatternFill

# ==========================================================
# INTERFAZ WEB "SF PANGEA v4.3.3" - OPERATIVE SUMMARY
# ==========================================================

st.set_page_config(page_title="SF PANGEA", page_icon="🚀", layout="wide")

# --- LOGIN DE SEGURIDAD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if not st.session_state.password_correct:
        st.title("🔐 Acceso Restringido - Alumbrado Público")
        pwd = st.text_input("Introduce la contraseña de acceso:", type="password")
        if st.button("Ingresar"):
            if pwd == "1827":
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
        return False
    return True

if check_password():
    st.title("🚀 SF PANGEA - Sistema de Optimización de Rutas")
    st.sidebar.header("Parámetros Operativos")
    t_unidad_min = st.sidebar.number_input("Minutos por Punto", value=20)
    v_ciu = st.sidebar.number_input("Velocidad Promedio (km/h)", value=25)
    BASE_COORDS = (19.291395219739588, -99.63555838631413)

    def get_real_route(coords_list):
        locs = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
        url = f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson"
        try:
            r = requests.get(url).json()
            if r['code'] == 'Ok':
                return r['routes'][0]['geometry']['coordinates'], r['routes'][0]['distance'] / 1000
        except: return None, None

    def normalizar_texto(texto):
        if not isinstance(texto, str): texto = str(texto)
        texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto.lower()

    def extraer_carga_robusta(punto_dict, tipo):
        d_letras = {'un ':'1 ','uno ':'1 ','una ':'1 ','dos ':'2 ','tres ':'3 ','cuatro ':'4 ','cinco ':'5 '}
        posibles_cols = ['ASUNTO', 'Observaciones', 'asunto', 'observaciones', 'Asunto']
        texto_fuente = ""
        for col in posibles_cols:
            if col in punto_dict and str(punto_dict[col]).strip() != "":
                texto_fuente = str(punto_dict[col])
                break
        t_norm = normalizar_texto(texto_fuente)
        for p, n in d_letras.items(): t_norm = t_norm.replace(p, n)
        patrones = {'lum': r'(\d+)\s*(?:lampara|foco|reflector|arbotante|luminari)', 'poste': r'(\d+)\s*(?:poste)', 'cable': r'(\d+)\s*(?:metro)'}
        m = re.search(patrones.get(tipo, ''), t_norm)
        return int(m.group(1)) if m else 0

    uploaded_file = st.file_uploader("Sube el archivo Excel o CSV de la brigada", type=["xlsx", "csv"])

    if uploaded_file:
        with st.spinner("Optimizando ruta..."):
            try:
                if uploaded_file.name.endswith('.xlsx'):
                    df_raw = pd.read_excel(uploaded_file, dtype=str).fillna("")
                else:
                    df_raw = pd.read_csv(uploaded_file, encoding='latin-1', dtype=str).fillna("")
            except:
                df_raw = pd.read_csv(uploaded_file, encoding='utf-8', dtype=str).fillna("")

            id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
            df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                pts = df_v.to_dict('records')
                idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
                ordenados = [pts.pop(idx_lejano)]
                while pts:
                    rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                    idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                    ordenados.append(pts.pop(idx))

                route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                geo_trazo, dist_real_km = get_real_route(route_coords)
                if not dist_real_km: dist_real_km = (len(ordenados) + 1) * 1.3

                for i, p in enumerate(ordenados, 1):
                    p['No_Ruta'], p['ID_Pangea_Nombre'] = i, p[id_col]
                    p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or 1
                    p['Cant_Postes'] = extraer_carga_robusta(p, 'poste')
                    p['Cant_Cable_m'] = extraer_carga_robusta(p, 'cable')

                tl, tp, tc = sum(x['Cant_Luminarias'] for x in ordenados), sum(x['Cant_Postes'] for x in ordenados), sum(x['Cant_Cable_m'] for x in ordenados)
                tm = ((tl + tp) * t_unidad_min) + ((dist_real_km / v_ciu) * 60)
                tstr = f"{int(tm//60)}h {int(tm%60)}min"

                df_f = pd.DataFrame(ordenados)
                vits = ['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m']
                cols_orig = [c for c in df_f.columns if c not in vits + ['lat_aux','lon_aux', id_col]]
                
                df_resumen = pd.DataFrame([
                    {'No_Ruta': '---', 'ID_Pangea_Nombre': '--- RESUMEN OPERATIVO ---'},
                    {'No_Ruta': 'Total Puntos:', 'ID_Pangea_Nombre': len(ordenados)},
                    {'No_Ruta': 'Total Lums:', 'ID_Pangea_Nombre': tl},
                    {'No_Ruta': 'Total Postes:', 'ID_Pangea_Nombre': tp},
                    {'No_Ruta': 'Total Cable:', 'ID_Pangea_Nombre': f"{tc} m"},
                    {'No_Ruta': 'Distancia:', 'ID_Pangea_Nombre': f"{round(dist_real_km,2)} km"},
                    {'No_Ruta': 'Tiempo:', 'ID_Pangea_Nombre': tstr}
                ])
                df_final_export = pd.concat([df_f[vits + cols_orig], df_resumen], ignore_index=True)

                output_xlsx = io.BytesIO()
                with pd.ExcelWriter(output_xlsx, engine='openpyxl') as writer:
                    df_final_export.to_excel(writer, index=False, sheet_name='Ruta')
                    ws = writer.sheets['Ruta']
                    fg, fa = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid"), PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
                    for r in range(2, len(ordenados) + 2):
                        try:
                            if int(df_f.iloc[r-2]['Cant_Postes']) > 0:
                                for cell in ws[r]: cell.fill = fg
                            elif int(df_f.iloc[r-2]['Cant_Cable_m']) > 0:
                                for cell in ws[r]: cell.fill = fa
                        except: pass

                kml = simplekml.Kml()
                capa = kml.newfolder(name="SF PANGEA")
                if geo_trazo:
                    ls = capa.newlinestring(name="Ruta Real", coords=geo_trazo)
                    ls.style.linestyle.width, ls.style.linestyle.color = 5, 'ff0000ff'
                for p in ordenados:
                    pnt = capa.newpoint(name=f"{p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
                    h = f"<![CDATA[<table border='1' style='font-size:11px; border-collapse:collapse; width:350px;'>"
                    h += f"<tr><td bgcolor='#f2f2f2' width='140'><b>No. Ruta</b></td><td><b>{p['No_Ruta']}</b></td></tr>"
                    for col in df_raw.columns:
                        if col not in ['lat_aux', 'lon_aux'] and str(p.get(col, "")).strip() != "":
                            h += f"<tr><td bgcolor='#f2f2f2'><b>{col}</b></td><td>{p[col]}</td></tr>"
                    h += f"<tr><td colspan='2' bgcolor='#004d40' style='color:white; text-align:center;'><b>RESUMEN OPERATIVO</b></td></tr>"
                    h += f"<tr><td><b>Distancia:</b></td><td>{round(dist_real_km,2)} km</td></tr>"
                    h += f"<tr><td><b>Tiempo:</b></td><td>{tstr}</td></tr></table>]]>"
                    pnt.description = h

                st.success("✅ Ruta procesada")
                st.download_button("📂 Descargar Excel (XLSX)", output_xlsx.getvalue(), "Ruta_Pangea.xlsx")
                st.download_button("🗺️ Descargar KML (Mapa)", kml.kml(), "Ruta_Pangea.kml")
