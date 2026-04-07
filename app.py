import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SF PANGEA v4.6.6", layout="wide")

# --- VARIABLES GLOBALES Y PARÁMETROS ---
BASE_COORDS = (19.291395219739588, -99.63555838631413)
URL_HOJA = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzEjSbMwxUm8/edit?gid=0#gid=0"
NOMBRE_HOJA = "Sheet1"
T_UNIDAD_MIN = 20  # Minutos por unidad (Lámpara/Poste)
V_CIU = 25         # Velocidad promedio en ciudad (km/h)

# --- MOTOR DE PROCESAMIENTO GEOGRÁFICO ---
def get_real_route(coords_list):
    """Obtiene el trazo real de las calles usando OSRM"""
    locs = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
    url = f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson"
    try:
        r = requests.get(url).json()
        if r['code'] == 'Ok':
            # Retorna el trazo (coordenadas) y la distancia en kilómetros
            return r['routes'][0]['geometry']['coordinates'], r['routes'][0]['distance'] / 1000
    except Exception as e:
        return None, None

# --- LÓGICA DE EXTRACCIÓN DE MATERIALES ---
def normalizar_texto(texto):
    """Limpia el texto de acentos y lo pasa a minúsculas"""
    if not isinstance(texto, str): 
        texto = str(texto)
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.lower()

def extraer_carga_robusta(punto_dict, tipo):
    """Analiza el ASUNTO u OBSERVACIONES para contar materiales"""
    d_letras = {'un ':'1 ','uno ':'1 ','una ':'1 ','dos ':'2 ','tres ':'3 ','cuatro ':'4 ','cinco ':'5 '}
    posibles_cols = ['ASUNTO', 'Observaciones', 'asunto', 'observaciones', 'Asunto', 'OBSERVACIONES']
    
    texto_fuente = ""
    for col in posibles_cols:
        if col in punto_dict and str(punto_dict[col]).strip() != "":
            texto_fuente = str(punto_dict[col])
            break
            
    t_norm = normalizar_texto(texto_fuente)
    for palabra, numero in d_letras.items():
        t_norm = t_norm.replace(palabra, numero)
        
    patrones = {
        'lum': r'(\d+)\s*(?:lampara|foco|reflector|arbotante|luminari[oa]|unidad|brazo)s?',
        'poste': r'(\d+)\s*(?:poste)s?',
        'cable': r'(\d+)\s*(?:metro)s?'
    }
    
    match = re.search(patrones[tipo], t_norm)
    return int(match.group(1)) if match else 0

# --- SISTEMA DE AUTENTICACIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.perfil = None
    st.session_state.usuario_nombre = ""

if not st.session_state.autenticado:
    st.title("🔐 Acceso SF PANGEA")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        u = st.text_input("Usuario")
    with col_l2:
        p = st.text_input("Contraseña", type="password")
    
    if st.button("🚀 Ingresar al Sistema", use_container_width=True):
        if u == "SF" and p == "1827":
            st.session_state.autenticado = True
            st.session_state.perfil = "ADMIN"
            st.session_state.usuario_nombre = "SF_ADMIN"
            st.rerun()
        elif u == "GuaDAP" and p == "5555":
            st.session_state.autenticado = True
            st.session_state.perfil = "CONSULTA"
            st.session_state.usuario_nombre = "GuaDAP"
            st.rerun()
        else:
            st.error("Credenciales no válidas. Intente de nuevo.")
else:
    # --- MENÚ LATERAL DE CONTROL ---
    with st.sidebar:
        st.header("⚙️ Panel Operativo")
        st.write(f"**Conectado como:** {st.session_state.usuario_nombre}")
        st.write(f"**Nivel de Acceso:** {st.session_state.perfil}")
        st.write("---")
        if st.button("🚪 Cerrar Sesión Segura", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.perfil = None
            st.rerun()
        st.write("---")
        st.info("SF PANGEA v4.6.6\nAyuntamiento de Toluca\nDirección de Alumbrado Público")

    # --- CUERPO PRINCIPAL ---
    st.title("🚀 SF PANGEA - Gestión Operativa")
    tab1, tab2 = st.tabs(["🆕 Generador de Rutas", "📂 Historial de Bitácora"])

    with tab1:
        if st.session_state.perfil == "CONSULTA":
            st.warning("⚠️ Perfil Restringido: El usuario **GuaDAP** solo tiene permisos de lectura en la bitácora.")
            st.image("https://cdn-icons-png.flaticon.com/512/3159/3159461.png", width=100)
        else:
            up = st.file_uploader("Subir Reporte de Brigada (Excel/CSV)", type=["csv", "xlsx"])
            if up:
                try:
                    # Lectura de Archivo
                    if up.name.endswith('.xlsx'):
                        df_raw = pd.read_excel(up, dtype=str).fillna("")
                    else:
                        df_raw = pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")

                    # Buscar columna de ID/Folio
                    id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                    
                    # Extracción de Coordenadas GPS
                    res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                    df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
                    df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
                    
                    df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

                    if not df_v.empty:
                        # --- ALGORITMO NEAREST NEIGHBOR ---
                        pts = df_v.to_dict('records')
                        idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
                        ordenados = [pts.pop(idx_lejano)]
                        
                        while pts:
                            rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                            idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                            ordenados.append(pts.pop(idx))

                        # --- TRAZADO Y CÁLCULOS ---
                        route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                        geo_trazo, dist_real_km = get_real_route(route_coords)
                        if not dist_real_km: 
                            dist_real_km = (len(ordenados) + 1) * 1.3

                        for i, p in enumerate(ordenados, 1):
                            p['No_Ruta'] = i
                            p['ID_Pangea_Nombre'] = p[id_col]
                            p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 and extraer_carga_robusta(p, 'cable')==0 else 0)
                            p['Cant_Postes'] = extraer_carga_robusta(p, 'poste')
                            p['Cant_Cable_m'] = extraer_carga_robusta(p, 'cable')
                            p['Maps'] = f"https://www.google.com/maps?q={p['lat_aux']},{p['lon_aux']}"

                        # Totales
                        tl = sum(x['Cant_Luminarias'] for x in ordenados)
                        tp = sum(x['Cant_Postes'] for x in ordenados)
                        tc = sum(x['Cant_Cable_m'] for x in ordenados)
                        
                        # Tiempo estimado
                        tm = ((tl + tp) * T_UNIDAD_MIN) + ((dist_real_km / V_CIU) * 60)
                        tstr = f"{int(tm//60)}h {int(tm%60)}min"

                        # --- CONSTRUCCIÓN DE EXPORTACIÓN ---
                        df_f = pd.DataFrame(ordenados)
                        vits = ['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']
                        cols_orig = [c for c in df_f.columns if c not in vits + ['lat_aux','lon_aux', id_col]]
                        
                        df_resumen = pd.DataFrame([
                            {'No_Ruta': '---', 'ID_Pangea_Nombre': '--- RESUMEN FINAL ---'},
                            {'No_Ruta': 'Total Puntos:', 'ID_Pangea_Nombre': len(ordenados)},
                            {'No_Ruta': 'Distancia:', 'ID_Pangea_Nombre': f"{round(dist_real_km,2)} km"},
                            {'No_Ruta': 'Tiempo:', 'ID_Pangea_Nombre': tstr}
                        ])
                        df_final_export = pd.concat([df_f[vits + cols_orig], df_resumen], ignore_index=True)

                        st.success(f"✅ ¡Ruta Generada! {len(ordenados)} puntos procesados.")

                        # --- BOTONES DE DESCARGA ---
                        c1, c2, c3, c4 = st.columns(4)

                        # EXCEL CON COLORES (Lógica de Alumbrado)
                        buf_xlsx = io.BytesIO()
                        with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
                            df_final_export.to_excel(writer, index=False, sheet_name='Ruta')
                            ws = writer.sheets['Ruta']
                            fg = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid") # Gris: Poste
                            fa = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid") # Azul: Cable
                            for r in range(2, len(ordenados) + 2):
                                try:
                                    if int(df_f.iloc[r-2]['Cant_Postes']) > 0:
                                        for cell in ws[r]: cell.fill = fg
                                    elif int(df_f.iloc[r-2]['Cant_Cable_m']) > 0:
                                        for cell in ws[r]: cell.fill = fa
                                except: pass
                        c1.download_button("📗 Excel Pro", buf_xlsx.getvalue(), file_name=f"{up.name}_PANGEA.xlsx", use_container_width=True)
                        
                        c2.download_button("📊 CSV Completo", df_final_export.to_csv(index=False).encode('utf-8-sig'), file_name=f"{up.name}_PANGEA.csv", use_container_width=True)

                        # KML MAESTRO (Globo HTML Detallado)
                        kml = simplekml.Kml()
                        fld = kml.newfolder(name="SF PANGEA")
                        if geo_trazo:
                            ls = fld.newlinestring(name="Trayectoria Vial", coords=geo_trazo)
                            ls.style.linestyle.width, ls.style.linestyle.color = 5, 'ff0000ff'
                        
                        for p in ordenados:
                            pnt = fld.newpoint(name=f"{p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
                            # Recuperamos TODA la información original para el globo
                            h = f"<![CDATA[<table border='1' style='font-size:11px; border-collapse:collapse; width:300px;'>"
                            h += f"<tr><td bgcolor='#f2f2f2'><b>No. Ruta</b></td><td><b>{p['No_Ruta']}</b></td></tr>"
                            for col in df_raw.columns:
                                if col not in ['lat_aux', 'lon_aux']:
                                    h += f"<tr><td>{col}</td><td>{p.get(col, '')}</td></tr>"
                            h += f"<tr><td colspan='2' bgcolor='#333' style='color:white; text-align:center;'><b>MATERIALES</b></td></tr>"
                            h += f"<tr><td>Luminarias:</td><td>{p['Cant_Luminarias']}</td></tr>"
                            h += f"<tr><td>Postes:</td><td>{p['Cant_Postes']}</td></tr>"
                            h += "</table>]]>"
                            pnt.description = h
                        c3.download_button("🗺️ KML Maestro", kml.kml(), file_name=f"{up.name}_PANGEA.kml", use_container_width=True)
                        
                        c4.link_button("🚀 My Maps", "https://www.google.com/maps/d/u/0/", use_container_width=True)

                        # --- REGISTRO DE BITÁCORA ---
                        if st.button("💾 REGISTRAR EN BITÁCORA GOOGLE"):
                            try:
                                conn = st.connection("gsheets", type=GSheetsConnection)
                                hist = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
                                
                                nueva_fila = pd.DataFrame([{
                                    "Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                                    "Nombre_Ruta": up.name,
                                    "Usuario_Generador": st.session_state.usuario_nombre,
                                    "Datos_JSON": f"Pts: {len(ordenados)}, Lums: {tl}, Poste: {tp}, Km: {round(dist_real_km,2)}"
                                }])
                                
                                conn.update(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, data=pd.concat([hist, nueva_fila], ignore_index=True))
                                st.balloons()
                                st.success(f"Bitácora actualizada por {st.session_state.usuario_nombre}")
                            except Exception as e:
                                st.error(f"Error de conexión: {e}")

                except Exception as e:
                    st.error(f"Error en el proceso: {e}")

    with tab2:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_hist = conn.read(spreadsheet=URL_HOJA, worksheet=NOMBRE_HOJA, ttl=0)
            st.write("### 📂 Historial Reciente de Operaciones")
            st.dataframe(df_hist.sort_index(ascending=False), use_container_width=True)
        except:
            st.info("Conectando con la base de datos de Google Sheets...")
