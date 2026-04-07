import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SF PANGEA v4.5.9", layout="wide")

BASE_COORDS = (19.291395219739588, -99.63555838631413)
URL_HOJA = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzeJSbMwxUm8/edit#gid=0"
NOMBRE_HOJA = "Sheet1"
T_UNIDAD_MIN, V_CIU = 20, 25 

# --- FUNCIONES DEL MOTOR (Basadas en v4.3.3) ---
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
    posibles_cols = ['ASUNTO', 'Observaciones', 'asunto', 'observaciones', 'Asunto', 'OBSERVACIONES']
    texto_fuente = ""
    for col in posibles_cols:
        if col in punto_dict and str(punto_dict[col]).strip() != "":
            texto_fuente = str(punto_dict[col]); break
    t_norm = normalizar_texto(texto_fuente)
    for p, n in d_letras.items(): t_norm = t_norm.replace(p, n)
    patrones = {
        'lum': r'(\d+)\s*(?:lampara|foco|reflector|arbotante|luminari[oa]|unidad|brazo)s?',
        'poste': r'(\d+)\s*(?:poste)s?',
        'cable': r'(\d+)\s*(?:metro)s?'
    }
    m = re.search(patrones[tipo], t_norm)
    return int(m.group(1)) if m else 0

# --- CONTROL DE ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso SF PANGEA")
    u, p = st.text_input("Usuario"), st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.rerun()
else:
    st.title("🚀 SF PANGEA - Dirección de Alumbrado")
    tab1, tab2 = st.tabs(["🆕 Generar Ruta", "📂 Historial de Bitácora"])

    with tab1:
        up = st.file_uploader("Subir Reporte (Excel/CSV)", type=["csv", "xlsx"])
        if up:
            try:
                # Lectura de datos
                df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
                id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                
                # Detección GPS
                res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
                df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

                if not df_v.empty:
                    # Lógica de proximidad (Punto 1 más lejano de la base)
                    pts = df_v.to_dict('records')
                    idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
                    ordenados = [pts.pop(idx_lejano)]
                    while pts:
                        rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                        idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                        ordenados.append(pts.pop(idx))

                    # Trazado vial OSRM y cálculos operativos
                    route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                    geo_trazo, dist_real_km = get_real_route(route_coords)
                    if not dist_real_km: dist_real_km = (len(ordenados) + 1) * 1.3

                    for i, p in enumerate(ordenados, 1):
                        p['No_Ruta'], p['ID_Pangea_Nombre'] = i, p[id_col]
                        p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 and extraer_carga_robusta(p, 'cable')==0 else 0)
                        p['Cant_Postes'] = extraer_carga_robusta(p, 'poste')
                        p['Cant_Cable_m'] = extraer_carga_robusta(p, 'cable')
                        p['Maps'] = f"https://www.google.com/maps?q={p['lat_aux']},{p['lon_aux']}"

                    # Totales para el Resumen
                    tl, tp, tc = sum(x['Cant_Luminarias'] for x in ordenados), sum(x['Cant_Postes'] for x in ordenados), sum(x['Cant_Cable_m'] for x in ordenados)
                    tm = ((tl + tp) * T_UNIDAD_MIN) + ((dist_real_km / V_CIU) * 60)
                    tstr = f"{int(tm//60)}h {int(tm%60)}min"

                    # Generación de DataFrame para Exportar
                    df_f = pd.DataFrame(ordenados)
                    vits = ['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']
                    cols_orig = [c for c in df_f.columns if c not in vits + ['lat_aux','lon_aux', id_col]]
                    
                    df_resumen = pd.DataFrame([
                        {'No_Ruta': '---', 'ID_Pangea_Nombre': '--- RESUMEN OPERATIVO ---'},
                        {'No_Ruta': 'Total Puntos:', 'ID_Pangea_Nombre': len(ordenados)},
                        {'No_Ruta': 'Total Lums:', 'ID_Pangea_Nombre': tl},
                        {'No_Ruta': 'Total Postes:', 'ID_Pangea_Nombre': tp},
                        {'No_Ruta': 'Total Cable:', 'ID_Pangea_Nombre': f"{tc} m"},
                        {'No_Ruta': 'Distancia:', 'ID_Pangea_Nombre': f"{round(dist_real_km,2)} km"},
                        {'No_Ruta': 'Tiempo Estimado:', 'ID_Pangea_Nombre': tstr}
                    ])
                    df_final_export = pd.concat([df_f[vits + cols_orig], df_resumen], ignore_index=True)

                    st.success(f"✅ Ruta Optimizada: {len(df_f)} puntos procesados correctamente.")

                    # --- GESTIÓN DE SALIDA (4 BOTONES) ---
                    st.write("### ⬇️ Descargar y Visualizar")
                    c1, c2, c3, c4 = st.columns(4)

                    # 1. Excel Pro (Con Colores)
                    buf_xlsx = io.BytesIO()
                    with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
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
                    c1.download_button("📗 Excel Pro", buf_xlsx.getvalue(), file_name=f"{up.name}_PANGEA.xlsx", use_container_width=True)

                    # 2. CSV Completo
                    c2.download_button("📊 CSV Completo", df_final_export.to_csv(index=False).encode('utf-8-sig'), file_name=f"{up.name}_PANGEA.csv", use_container_width=True)

                    # 3. KML Maestro (Con Desglose y Trazo)
                    kml = simplekml.Kml()
                    fld = kml.newfolder(name="SF PANGEA")
                    if geo_trazo:
                        ls = fld.newlinestring(name="Trayectoria Vial", coords=geo_trazo)
                        ls.style.linestyle.width, ls.style.linestyle.color = 5, 'ff0000ff' # Rojo
                    
                    for p in ordenados:
                        pnt = fld.newpoint(name=f"{p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
                        # Construcción de Tabla HTML para el KML
                        h = f"<![CDATA[<table border='1' style='font-size:11px; border-collapse:collapse; width:320px;'>"
                        h += f"<tr><td bgcolor='#f2f2f2' width='120'><b>No. Ruta</b></td><td><b>{p['No_Ruta']}</b></td></tr>"
                        for col in df_raw.columns:
                            if col not in ['lat_aux', 'lon_aux'] and str(p.get(col, "")).strip() != "":
                                h += f"<tr><td bgcolor='#f2f2f2'><b>{col}</b></td><td>{p[col]}</td></tr>"
                        # Desglose de materiales
                        h += f"<tr><td colspan='2' bgcolor='#333' style='color:white; text-align:center;'><b>DESGLOSE DE MATERIALES</b></td></tr>"
                        h += f"<tr><td><b>Luminarias:</b></td><td>{p['Cant_Luminarias']}</td></tr>"
                        h += f"<tr><td><b>Postes:</b></td><td>{p['Cant_Postes']}</td></tr>"
                        h += f"<tr><td><b>Cable (m):</b></td><td>{p['Cant_Cable_m']}</td></tr>"
                        # Resumen Operativo completo en el punto
                        h += f"<tr><td colspan='2' bgcolor='#004d40' style='color:white; text-align:center;'><b>RESUMEN OPERATIVO</b></td></tr>"
                        h += f"<tr><td><b>Total Lums:</b></td><td>{tl}</td></tr>"
                        h += f"<tr><td><b>Total Postes:</b></td><td>{tp}</td></tr>"
                        h += f"<tr><td><b>Distancia Ruta:</b></td><td>{round(dist_real_km,2)} km</td></tr>"
                        h += f"<tr><td><b>Tiempo Est.:</b></td><td>{tstr}</td></tr>"
                        h += f"</table>]]>"
                        pnt.description = h
                    
                    c3.download_button("🗺️ KML Maestro", kml.kml(), file_name=f"{up.name}_PANGEA.kml", use_container_width=True)

                    # 4. Acceso Directo a My Maps (Versión Estable)
                    c4.link_button("🚀 Abrir My Maps", "https://www.google.com/maps/d/u/0/", use_container_width=True, type="primary")

                    if st.button("💾 REGISTRAR EN BITÁCORA"):
                        try:
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            hist = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
                            nueva = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Nombre_Ruta": up.name, "Puntos": len(df_f), "Distancia": round(dist_real_km,2)}])
                            conn.update(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, data=pd.concat([hist, nueva], ignore_index=True))
                            st.balloons(); st.success("Sincronizado con GSheets.")
                        except: st.error("Error al conectar con la bitácora.")

            except Exception as e: st.error(f"Error procesando el archivo: {e}")

    with tab2:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_hist = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
            st.dataframe(df_hist.sort_index(ascending=False), use_container_width=True)
        except: st.info("Cargando bitácora...")
