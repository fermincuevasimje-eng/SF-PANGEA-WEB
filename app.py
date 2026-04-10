import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time, random
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

# --- 1. CONFIGURACIÓN E INTERFAZ (MARCA DE AGUA SF) ---
st.set_page_config(page_title="SF PANGEA v4.8.50", layout="wide")

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

BASE_COORDS = (19.291395219739588, -99.63555838631413)
URL_DB = "https://docs.google.com/spreadsheets/d/14_fewol5DiFXoiO102wviiWR08Lw3PKHzEjSbMwxUm8/edit?gid=0#gid=0"
HOJA_PRINCIPAL = "Sheet1"
HOJA_PAPELERA = "Trash"

CHISTES = [
    "— ¿Qué le dice un jaguar a otro jaguar? — Jaguar you.",
    "— ¿Cómo se dice pañuelo en japonés? — Sakamoco.",
    "— ¿Qué hace un perro con un taladro? — Adiestrando.",
    "— ¿Qué hace una abeja en el gimnasio? — Zumba.",
    "— ¿Cómo se queda un mago después de comer? — Magordito."
]

# --- 2. MOTOR LÓGICO ---
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
        if any(w in t_norm for w in ['cable', 'conductor', 'linea', 'red']):
            m_flex = re.search(r'(\d+)\s*(?:metro|m)s?', t_norm)
            return int(m_flex.group(1)) if m_flex else 0
        return 0
    m = re.search(patrones[tipo], t_norm)
    return int(m.group(1)) if m else 0

# --- 3. AUTENTICACIÓN Y ESTADO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = False, None, ""
if "menu" not in st.session_state:
    st.session_state.menu = "Inicio"

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
        else: st.error("Acceso denegado")
else:
    # --- 4. SIDEBAR ---
    with st.sidebar:
        st.title("⚙️ Panel Operativo")
        st.write(f"**Usuario:** {st.session_state.usuario_nombre}")
        st.write("---")
        if st.button("🏠 Inicio", use_container_width=True): st.session_state.menu = "Inicio"
        if st.button("🚀 GdR", use_container_width=True): st.session_state.menu = "GdR"
        if st.button("📁 SF2", use_container_width=True): st.session_state.menu = "SF2"
        if st.button("📊 SF3", use_container_width=True): st.session_state.menu = "SF3"
        st.write("---")
        if st.session_state.menu == "GdR":
            st.subheader("📊 Ajustes GdR")
            t_por_punto = st.slider("Minutos por Atención", 5, 60, 20)
            v_promedio = st.slider("Velocidad km/h", 10, 80, 25)
            st.write("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()

    # --- 5. CUERPO LÓGICO ---
    if st.session_state.menu == "Inicio":
        st.title("👋 Bienvenido a SF PANGEA")
        st.info("Sistema de Gestión Operativa")

    elif st.session_state.menu == "GdR":
        st.title("🚀 GdR - Generador de Rutas")
        tab1, tab2, tab3 = st.tabs(["🆕 Nueva Ruta", "📂 Bitácora", "🗑️ Papelera"])

        with tab1:
            up = st.file_uploader("Subir Archivo", type=["csv", "xlsx"])
            if up:
                try:
                    df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
                    id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                    res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                    df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
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

                        total_lums, total_postes = 0, 0
                        for i, p in enumerate(ordenados, 1):
                            p['No_Ruta'], p['ID_Pangea_Nombre'] = i, p[id_col]
                            p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 else 0)
                            p['Cant_Postes'], p['Cant_Cable_m'] = extraer_carga_robusta(p, 'poste'), extraer_carga_robusta(p, 'cable')
                            p['Maps'] = f"https://www.google.com/maps?q={p['lat_aux']},{p['lon_aux']}"
                            total_lums += p['Cant_Luminarias']; total_postes += p['Cant_Postes']

                        min_totales = ((total_lums + total_postes) * t_por_punto) + (dist_real_km / v_promedio * 60)
                        tiempo_abr = f"{int(min_totales // 60)} h {int(min_totales % 60)} m"
                        
                        df_f = pd.DataFrame(ordenados)
                        cols_vits = ['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']
                        cols_orig = [c for c in df_raw.columns if c not in ['lat_aux', 'lon_aux']]
                        
                        st.success(f"✅ Ruta optimizada: {len(ordenados)} puntos.")
                        c1, c2, c3, c4 = st.columns(4)

                        # Excel
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                            df_f[cols_vits + [c for c in cols_orig if c != id_col]].to_excel(writer, index=False, sheet_name='Ruta')
                            ws = writer.sheets['Ruta']
                            l_r = len(ordenados) + 1
                            ws.cell(row=l_r+2, column=2, value="--- RESUMEN DINÁMICO ---")
                            ws.cell(row=l_r+3, column=1, value="Luminarias:"); ws.cell(row=l_r+3, column=2, value=f"=SUM(C2:C{l_r})")
                            ws.cell(row=l_r+4, column=1, value="Postes:"); ws.cell(row=l_r+4, column=2, value=f"=SUM(D2:D{l_r})")
                            ws.cell(row=l_r+5, column=1, value="Distancia:"); ws.cell(row=l_r+5, column=2, value=f"{round(dist_real_km,2)} km")
                            ws.cell(row=l_r+6, column=1, value="Tiempo:"); ws.cell(row=l_r+6, column=2, value=tiempo_abr)
                            fill_p, fill_c = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid"), PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
                            for r in range(2, l_r + 1):
                                if int(df_f.iloc[r-2]['Cant_Postes']) > 0:
                                    for cell in ws[r]: cell.fill = fill_p
                                elif int(df_f.iloc[r-2]['Cant_Cable_m']) > 0:
                                    for cell in ws[r]: cell.fill = fill_c

                        c1.download_button("📗 Excel", buf.getvalue(), file_name=f"SF_{up.name}.xlsx")
                        c2.download_button("📊 CSV", df_f[cols_vits + [c for c in cols_orig if c != id_col]].to_csv(index=False).encode('utf-8-sig'), file_name=f"SF_{up.name}.csv")

                        # KML
                        kml = simplekml.Kml()
                        if geo_trazo:
                            ls = kml.newlinestring(name="Ruta", coords=geo_trazo)
                            ls.style.linestyle.width, ls.style.linestyle.color = 5, 'ff0000ff'
                        for p in ordenados:
                            pnt = kml.newpoint(name=f"{p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
                            desc = f"Punto: {p['No_Ruta']}\nLums: {p['Cant_Luminarias']}\nPostes: {p['Cant_Postes']}\nCable: {p['Cant_Cable_m']}m\nDistancia: {round(dist_real_km,2)}km\nTiempo: {tiempo_abr}"
                            pnt.description = desc
                        
                        c3.download_button("🗺️ KML", kml.kml(), file_name=f"SF_{up.name}.kml")
                        c4.link_button("🚀 My Maps", "http://google.com/maps/d/")

                        if st.button("💾 REGISTRAR"):
                            try:
                                conn = st.connection("gsheets", type=GSheetsConnection)
                                hist = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                                info_j = f"Pts: {len(ordenados)}, Lums: {total_lums}, Km: {round(dist_real_km,2)}, T: {tiempo_abr}"
                                n_f = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Nombre_Ruta": up.name, "Usuario_Generador": st.session_state.usuario_nombre, "Datos_JSON": info_j}])
                                conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([hist, n_f], ignore_index=True))
                                st.balloons()
                            except: st.error("Error GSheets")
                except: st.error("Error archivo")

        with tab2: # Bitácora
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_bt = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                if not df_bt.empty:
                    df_bt_v = df_bt.copy()
                    df_bt_v.insert(0, "ID_Reg", range(1, len(df_bt_v) + 1))
                    if st.session_state.perfil == "ADMIN":
                        ids = st.multiselect("Mover a papelera:", df_bt_v["ID_Reg"].tolist())
                        if st.button("🗑️"):
                            idx = df_bt_v[df_bt_v["ID_Reg"].isin(ids)].index
                            df_tr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, ttl=0).dropna(how='all')
                            conn.update(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, data=pd.concat([df_tr, df_bt.loc[idx]], ignore_index=True))
                            conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=df_bt.drop(idx))
                            st.rerun()
                    st.dataframe(df_bt_v.sort_values("ID_Reg", ascending=False), hide_index=True)
            except: st.info("Sincronizando...")

        with tab3: # Papelera
            if st.session_state.perfil == "ADMIN":
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_tr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, ttl=0).dropna(how='all')
                    if not df_tr.empty:
                        df_tr_v = df_tr.copy()
                        df_tr_v.insert(0, "ID_Reg", range(1, len(df_tr_v) + 1))
                        ids_r = st.multiselect("Restaurar:", df_tr_v["ID_Reg"].tolist())
                        if st.button("♻️"):
                            idx_r = df_tr_v[df_tr_v["ID_Reg"].isin(ids_r)].index
                            df_pr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                            conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([df_pr, df_tr.loc[idx_r]], ignore_index=True))
                            conn.update(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, data=df_tr.drop(idx_r))
                            st.rerun()
                        st.dataframe(df_tr_v)
                except: st.info("Cargando...")
