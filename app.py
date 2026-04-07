import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="SF PANGEA v4.7.1", layout="wide")

# Coordenadas de la Dirección de Alumbrado Público Toluca
BASE_COORDS = (19.291395219739588, -99.63555838631413)
URL_DB = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzEjSbMwxUm8/edit?gid=0#gid=0"
HOJA_PRINCIPAL = "Sheet1"
HOJA_PAPELERA = "Trash" # Asegúrate de que esta hoja exista en tu archivo

# --- 2. MOTOR GEOGRÁFICO Y EXTRACCIÓN (LÓGICA GANADA) ---
def get_real_route(coords_list):
    """Calcula el trazo real por calles usando OSRM"""
    locs = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
    url = f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson"
    try:
        r = requests.get(url).json()
        if r['code'] == 'Ok':
            return r['routes'][0]['geometry']['coordinates'], r['routes'][0]['distance'] / 1000
    except:
        return None, None

def normalizar_texto(texto):
    """Limpia texto para análisis de materiales"""
    if not isinstance(texto, str): texto = str(texto)
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.lower()

def extraer_carga_robusta(punto_dict, tipo):
    """Extrae cantidades de lámparas, postes o cable del texto"""
    d_letras = {'un ':'1 ','uno ':'1 ','una ':'1 ','dos ':'2 ','tres ':'3 ','cuatro ':'4 ','cinco ':'5 '}
    posibles_cols = ['ASUNTO', 'Observaciones', 'asunto', 'observaciones', 'Asunto', 'OBSERVACIONES']
    texto_fuente = ""
    for col in posibles_cols:
        if col in punto_dict and str(punto_dict[col]).strip() != "":
            texto_fuente = str(punto_dict[col])
            break
    t_norm = normalizar_texto(texto_fuente)
    for p, n in d_letras.items(): t_norm = t_norm.replace(p, n)
    patrones = {
        'lum': r'(\d+)\s*(?:lampara|foco|reflector|arbotante|luminari[oa]|unidad|brazo)s?',
        'poste': r'(\d+)\s*(?:poste)s?',
        'cable': r'(\d+)\s*(?:metro)s?'
    }
    m = re.search(patrones[tipo], t_norm)
    return int(m.group(1)) if m else 0

# --- 3. GESTIÓN DE SESIÓN Y LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.perfil = None
    st.session_state.usuario_nombre = ""

if not st.session_state.autenticado:
    st.title("🔐 Acceso SF PANGEA")
    col_u, col_p = st.columns(2)
    with col_u: u = st.text_input("Usuario")
    with col_p: p = st.text_input("Contraseña", type="password")
    
    if st.button("🚀 Ingresar", use_container_width=True):
        if u == "SF" and p == "1827":
            st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = True, "ADMIN", "SF_ADMIN"
            st.rerun()
        elif u == "GuaDAP" and p == "5555":
            st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = True, "CONSULTA", "GuaDAP"
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

else:
    # --- 4. PANEL LATERAL (NUEVOS CONTROLES) ---
    with st.sidebar:
        st.title("⚙️ Panel Operativo")
        st.write(f"**Usuario:** {st.session_state.usuario_nombre}")
        st.write(f"**Perfil:** {st.session_state.perfil}")
        st.write("---")
        
        st.subheader("📊 Ajustes de Rendimiento")
        t_por_punto = st.slider("Minutos por Punto (Atención)", 5, 60, 20, help="Tiempo que tarda la grúa en cada lámpara")
        v_promedio = st.slider("Velocidad de Traslado (km/h)", 10, 80, 25, help="Velocidad media de las unidades en Toluca")
        
        st.write("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
        st.info("SF PANGEA v4.7.1")

    # --- 5. CUERPO DE LA APLICACIÓN ---
    st.title("🚀 SF PANGEA - Dirección de Alumbrado")
    tab1, tab2, tab3 = st.tabs(["🆕 Generar Ruta", "📂 Bitácora", "🗑️ Papelera (Admin)"])

    with tab1:
        if st.session_state.perfil == "CONSULTA":
            st.warning("⚠️ Acceso Restringido: Tu perfil no permite generar nuevas rutas.")
        else:
            up = st.file_uploader("Subir Reporte (Excel/CSV)", type=["csv", "xlsx"])
            if up:
                try:
                    # Lectura y GPS
                    df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
                    id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                    res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                    df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
                    df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

                    if not df_v.empty:
                        # Algoritmo NN
                        pts = df_v.to_dict('records')
                        idx_lejano = np.argmax(cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0])
                        ordenados = [pts.pop(idx_lejano)]
                        while pts:
                            rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                            idx = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], rest))
                            ordenados.append(pts.pop(idx))

                        # Trazo Vial y Cálculos (Usando Sliders)
                        route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                        geo_trazo, dist_real_km = get_real_route(route_coords)
                        if not dist_real_km: dist_real_km = (len(ordenados) + 1) * 1.3

                        for i, p in enumerate(ordenados, 1):
                            p['No_Ruta'], p['ID_Pangea_Nombre'] = i, p[id_col]
                            p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 and extraer_carga_robusta(p, 'cable')==0 else 0)
                            p['Cant_Postes'], p['Cant_Cable_m'] = extraer_carga_robusta(p, 'poste'), extraer_carga_robusta(p, 'cable')
                            p['Maps'] = f"https://www.google.com/maps?q={p['lat_aux']},{p['lon_aux']}"

                        # Totales y Tiempo (Usando Sliders)
                        tl, tp, tc = sum(x['Cant_Luminarias'] for x in ordenados), sum(x['Cant_Postes'] for x in ordenados), sum(x['Cant_Cable_m'] for x in ordenados)
                        tiempo_min = ((tl + tp) * t_por_punto) + ((dist_real_km / v_promedio) * 60)
                        tiempo_str = f"{int(tiempo_min//60)}h {int(tiempo_min%60)}min"

                        # --- EXPORTACIÓN RECUPERADA ---
                        df_f = pd.DataFrame(ordenados)
                        vits = ['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']
                        cols_orig = [c for c in df_f.columns if c not in vits + ['lat_aux','lon_aux', id_col]]
                        
                        df_resumen = pd.DataFrame([
                            {'No_Ruta': '---', 'ID_Pangea_Nombre': '--- RESUMEN OPERATIVO ---'},
                            {'No_Ruta': 'Total Puntos:', 'ID_Pangea_Nombre': len(ordenados)},
                            {'No_Ruta': 'Total Lums:', 'ID_Pangea_Nombre': tl},
                            {'No_Ruta': 'Total Postes:', 'ID_Pangea_Nombre': tp},
                            {'No_Ruta': 'Total Cable:', 'ID_Pangea_Nombre': f"{tc} m"},
                            {'No_Ruta': 'Distancia Real:', 'ID_Pangea_Nombre': f"{round(dist_real_km,2)} km"},
                            {'No_Ruta': 'Tiempo Estimado:', 'ID_Pangea_Nombre': tiempo_str}
                        ])
                        df_final_export = pd.concat([df_f[vits + cols_orig], df_resumen], ignore_index=True)

                        st.success(f"✅ Ruta optimizada para {len(ordenados)} puntos.")
                        
                        # Botones de Salida
                        c1, c2, c3, c4 = st.columns(4)
                        
                        # Excel con Colores
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
                        c2.download_button("📊 CSV Completo", df_final_export.to_csv(index=False).encode('utf-8-sig'), file_name=f"{up.name}_PANGEA.csv", use_container_width=True)

                        # KML Maestro (Globo HTML Completo)
                        kml = simplekml.Kml()
                        fld = kml.newfolder(name="SF PANGEA")
                        if geo_trazo:
                            ls = fld.newlinestring(name="Trayectoria Vial", coords=geo_trazo)
                            ls.style.linestyle.width, ls.style.linestyle.color = 5, 'ff0000ff'
                        for p in ordenados:
                            pnt = fld.newpoint(name=f"{p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
                            h = f"<![CDATA[<table border='1' style='font-size:11px; width:280px;'><tr><td bgcolor='#f2f2f2'><b>Folio</b></td><td>{p['ID_Pangea_Nombre']}</td></tr>"
                            for col in df_raw.columns:
                                if col not in ['lat_aux','lon_aux']: h += f"<tr><td>{col}</td><td>{p[col]}</td></tr>"
                            h += f"<tr><td bgcolor='#333' style='color:white;'><b>Tiempo Est.</b></td><td>{tiempo_str}</td></tr></table>]]>"
                            pnt.description = h
                        c3.download_button("🗺️ KML Maestro", kml.kml(), file_name=f"{up.name}_PANGEA.kml", use_container_width=True)
                        c4.link_button("🚀 My Maps", "https://www.google.com/maps/d/u/0/", use_container_width=True)

                        # Registro en Bitácora con TIEMPO y JSON completo
                        if st.button("💾 REGISTRAR EN BITÁCORA"):
                            try:
                                conn = st.connection("gsheets", type=GSheetsConnection)
                                hist = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0)
                                info_j = f"Pts: {len(ordenados)}, Lums: {tl}, Poste: {tp}, Km: {round(dist_real_km,2)}, Tiempo: {tiempo_str}"
                                nueva_fila = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Nombre_Ruta": up.name, "Usuario_Generador": st.session_state.usuario_nombre, "Datos_JSON": info_j}])
                                conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([hist, nueva_fila], ignore_index=True))
                                st.balloons(); st.success("Bitácora actualizada.")
                            except Exception as e: st.error(f"Error: {e}")

                except Exception as e: st.error(f"Error crítico: {e}")

    with tab2:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_bt = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
            st.write("### Historial de Bitácora")
            if st.session_state.perfil == "ADMIN" and not df_bt.empty:
                sel = st.multiselect("Registros para mover a papelera:", df_bt.index)
                if st.button("🗑️ Eliminar y mover a papelera"):
                    df_tr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, ttl=0).dropna(how='all')
                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, data=pd.concat([df_tr, df_bt.loc[sel]], ignore_index=True))
                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=df_bt.drop(sel))
                    st.success("Movido a papelera."); st.rerun()
            st.dataframe(df_bt.sort_index(ascending=False), use_container_width=True)
        except: st.info("Sincronizando...")

    with tab3:
        if st.session_state.perfil == "ADMIN":
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_tr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, ttl=0).dropna(how='all')
                st.write("### Papelera de Reciclaje")
                if not df_tr.empty:
                    rec = st.multiselect("Restaurar registros:", df_tr.index)
                    if st.button("♻️ Restaurar ahora"):
                        df_pr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                        conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([df_pr, df_tr.loc[rec]], ignore_index=True))
                        conn.update(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, data=df_tr.drop(rec))
                        st.success("Restaurado."); st.rerun()
                st.dataframe(df_tr, use_container_width=True)
            except: st.info("Cargando papelera...")
        else: st.warning("Área restringida para Administradores.")
