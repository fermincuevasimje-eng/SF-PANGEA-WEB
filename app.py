import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time, random
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="SF PANGEA v4.8.29", layout="wide")

# Marca de agua y estilo
st.markdown(
    """
    <style>
    .main::before {
        content: "SF";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-45deg);
        font-size: 25vw;
        color: rgba(0, 0, 0, 0.07);
        z-index: -1;
        pointer-events: none;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Constantes técnicas
BASE_COORDS = (19.291395219739588, -99.63555838631413)
URL_DB = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzEjSbMwxUm8/edit?gid=0#gid=0"
HOJA_PRINCIPAL = "Sheet1"
HOJA_PAPELERA = "Trash"

# --- 2. FUNCIONES DE APOYO ---
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
        'lum': r'(\d+)\s*(?:lampara|foco|reflector|arbotante|luminari[oa]|unidad|brazo|farol[a]?|punto de luz)s?',
        'poste': r'(\d+)\s*(?:poste|estructura|columna)s?',
        'cable': r'(\d+)\s*(?:metro|m)\.?\s*(?:de\s*)?(?:cable|conductor|linea|red|alambre|potencia)s?'
    }
    if tipo == 'cable':
        m = re.search(patrones['cable'], t_norm)
        if m: return int(m.group(1))
        return 0
    m = re.search(patrones[tipo], t_norm)
    return int(m.group(1)) if m else 0

# --- 3. GESTIÓN DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.update({"autenticado": False, "perfil": None, "usuario": "", "menu": "Inicio"})

if not st.session_state.autenticado:
    st.title("🔐 Acceso SF PANGEA")
    c1, c2 = st.columns(2)
    u = c1.text_input("Usuario")
    p = c2.text_input("Contraseña", type="password")
    if st.button("🚀 Ingresar", use_container_width=True):
        if u == "SF" and p == "1827":
            st.session_state.update({"autenticado": True, "perfil": "ADMIN", "usuario": "SF_ADMIN"})
            st.rerun()
        elif u == "GuaDAP" and p == "5555":
            st.session_state.update({"autenticado": True, "perfil": "CONSULTA", "usuario": "GuaDAP"})
            st.rerun()
        else: st.error("Credenciales incorrectas")
else:
    # --- 4. SIDEBAR Y MENÚ ---
    with st.sidebar:
        st.title(f"👤 {st.session_state.usuario}")
        st.write("---")
        if st.button("🏠 Inicio", use_container_width=True): st.session_state.menu = "Inicio"
        if st.button("🚀 GdR (Rutas)", use_container_width=True): st.session_state.menu = "GdR"
        if st.button("📂 Bitácora GSheets", use_container_width=True): st.session_state.menu = "Bitacora"
        st.write("---")
        if st.session_state.menu == "GdR":
            t_por_punto = st.slider("Minutos por Atención", 5, 60, 20)
            v_promedio = st.slider("Velocidad Promedio (km/h)", 10, 80, 25)
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()

    # --- 5. MÓDULO GENERADOR DE RUTAS (GdR) ---
    if st.session_state.menu == "GdR":
        st.title("🚀 Generador de Rutas Pro")
        up = st.file_uploader("Cargar archivo de puntos", type=["xlsx", "csv"])
        
        if up:
            df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
            cols_originales = [c for c in df_raw.columns if not c.startswith('lat_aux')]
            id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
            
            # Detección de GPS
            res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
            df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
            df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

            if not df_v.empty:
                # Lógica de optimización
                pts = df_v.to_dict('records')
                idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
                ordenados = [pts.pop(idx_lejano)]
                while pts:
                    rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                    idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                    ordenados.append(pts.pop(idx))

                route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                geo_trazo, dist_km = get_real_route(route_coords)
                if not dist_km: dist_km = (len(ordenados) + 1) * 1.2

                total_lums = 0; total_postes = 0; total_cable = 0
                for i, p in enumerate(ordenados, 1):
                    p['No_Ruta'] = i
                    p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 and extraer_carga_robusta(p, 'cable')==0 else 0)
                    p['Cant_Postes'] = extraer_carga_robusta(p, 'poste')
                    p['Cant_Cable_m'] = extraer_carga_robusta(p, 'cable')
                    total_lums += p['Cant_Luminarias']; total_postes += p['Cant_Postes']; total_cable += p['Cant_Cable_m']

                tiempo_total_min = ((total_lums + total_postes) * t_por_punto) + (dist_km / v_promedio * 60)
                tiempo_str = f"{int(tiempo_total_min // 60)}h {int(tiempo_total_min % 60)}m"

                # --- 6. EXCEL VIVO (FÓRMULAS) ---
                buf_xlsx = io.BytesIO()
                with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
                    df_final = pd.DataFrame(ordenados)
                    cols_vista = ['No_Ruta', id_col, 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m']
                    df_final[cols_vista + [c for c in cols_originales if c not in cols_vista]].to_excel(writer, index=False, sheet_name='Ruta SF')
                    ws = writer.sheets['Ruta SF']
                    last = len(ordenados) + 1
                    # Resumen en Excel
                    ws.cell(row=last+2, column=2, value="RESUMEN OPERATIVO")
                    ws.cell(row=last+3, column=1, value="Total Luminarias:"); ws.cell(row=last+3, column=2, value=f"=SUM(C2:C{last})")
                    ws.cell(row=last+4, column=1, value="Tiempo Est:"); ws.cell(row=last+4, column=2, value=tiempo_str)
                    # Colores
                    for r in range(2, last + 1):
                        if int(df_final.iloc[r-2]['Cant_Postes']) > 0:
                            for cell in ws[r]: cell.fill = PatternFill("solid", start_color="E2E2E2")

                # --- 7. KML PROFESIONAL (ORDEN SOLICITADO) ---
                kml = simplekml.Kml()
                fld = kml.newfolder(name="SF PANGEA")
                if geo_trazo:
                    ls = fld.newlinestring(name="Trayectoria Vial", coords=geo_trazo)
                    ls.style.linestyle.width, ls.style.linestyle.color = 5, 'ff0000ff'

                for p in ordenados:
                    pnt = fld.newpoint(name=f"P{p['No_Ruta']} - {p[id_col]}", coords=[(p['lon_aux'], p['lat_aux'])])
                    # Construcción del Globo de Información
                    h = "<![CDATA[<table border='1' style='width:320px; border-collapse:collapse; font-family:Arial; font-size:12px;'>"
                    # Parte A: DESGLOSE
                    h += f"<tr><td bgcolor='#1F4E78' colspan='2' align='center'><b style='color:white;'>DESGLOSE OPERATIVO</b></td></tr>"
                    h += f"<tr><td bgcolor='#D9EAD3'><b>Luminarias SF:</b></td><td>{p['Cant_Luminarias']}</td></tr>"
                    h += f"<tr><td bgcolor='#D9EAD3'><b>Postes SF:</b></td><td>{p['Cant_Postes']}</td></tr>"
                    h += f"<tr><td bgcolor='#D9EAD3'><b>Cable SF:</b></td><td>{p['Cant_Cable_m']} m</td></tr>"
                    # Parte B: INFORMACIÓN ORIGINAL
                    h += f"<tr><td bgcolor='#767171' colspan='2' align='center'><b style='color:white;'>INFORMACIÓN DEL PUNTO</b></td></tr>"
                    for col in cols_originales:
                        h += f"<tr><td bgcolor='#F2F2F2'><b>{col}:</b></td><td>{p.get(col, '')}</td></tr>"
                    # Parte C: RESUMEN OPERATIVO FINAL
                    h += f"<tr><td bgcolor='#C00000' colspan='2' align='center'><b style='color:white;'>RESUMEN GENERAL</b></td></tr>"
                    h += f"<tr><td><b>Distancia:</b></td><td>{round(dist_km,2)} km</td></tr>"
                    h += f"<tr><td><b>Tiempo Ruta:</b></td><td>{tiempo_str}</td></tr>"
                    h += "</table>]]>"
                    pnt.description = h

                # --- 8. DESCARGAS Y BITÁCORA ---
                c1, c2, c3 = st.columns(3)
                c1.download_button("📗 Excel Vivo", buf_xlsx.getvalue(), file_name=f"SF_VIVO_{up.name}.xlsx", use_container_width=True)
                c2.download_button("🗺️ KML Maestro", kml.kml(), file_name=f"SF_KML_{up.name}.kml", use_container_width=True)
                if c3.button("💾 Guardar Bitácora", use_container_width=True):
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        df_b = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL).dropna(how='all')
                        nuevo = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Ruta": up.name, "Puntos": len(ordenados), "Lums": total_lums}])
                        conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([df_b, nuevo]))
                        st.success("Guardado en GSheets")
                    except: st.error("Error de conexión")

    elif st.session_state.menu == "Inicio":
        st.title("Bienvenido a SF PANGEA")
        st.info("Sistema de optimización logística para Alumbrado Público.")
