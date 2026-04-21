import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time, random
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

# --- 1. CONFIGURACIÓN E INTERFAZ (MARCA DE AGUA SF) ---
st.set_page_config(page_title="SF PANGEA V1", layout="wide")

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
    /* Estilo para las métricas */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #1f4e78;
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

# --- 1.5 CATÁLOGO MAESTRO (BASE DE DATOS COMPLETA: 48 DELEGACIONES) ---
CATALOGO_MAESTRO = {
    "ADOLFO LOPEZ MATEOS": ['PARQUES NACIONALES I', 'MIGUEL HIDALGO  (CORRALITOS)', 'PARQUES NACIONALES  I I'],
    "ARBOL DE LAS MANITAS": ['ZOPILOCALCO SUR', 'ZOPILOCALCO NORTE', 'LOMAS ALTAS', 'HUITZILA Y DOCTORES', 'NIÑOS HEROES (PENSIONES)'],
    "BARRIO TRADICIONALES": ['SANTA BARBARA', 'EL COPORO', 'LA RETAMA', 'SAN MIGUEL APINAHUISCO', 'UNION', 'SAN LUIS OBISPO'],
    "CACALOMACAN": ['CENTRO', 'RANCHO SAN MIGUEL ZACANGO', 'SAGRADO CORAZON', 'EL ARENAL'],
    "CALIXTLAHUACA": ['SAN FRANCISCO DE ASIS', 'ZONA ARQUEOLOGICA', 'EL CALVARIO', 'PALMILLAS'],
    "CAPULTITLAN": ['SAN ISIDRO LABRADOR', 'PASEOS DEL  VALLE', 'SAN JUDAS TADEO', 'LA SOLEDAD', 'LOS PINOS', 'GUADALUPE'],
    "CENTRO HISTORICO": ['CENTRO', 'SANTA CLARA', '5 DE MAYO', 'FRANCISCO MURGUIA (EL RANCHITO)', 'LA MERCED ( ALAMEDA)'],
    "CERRILLO VISTA HERMOSA": ['EL CERRILLO', 'EL EMBARCADERO'],
    "CIUDAD UNIVERSITARIA": ['PLAZAS DE SAN BUENAVENTURA', 'SAN BERNARDINO', 'VICENTE GUERRERO'],
    "COLON": ['COLON Y CIPRES I', 'COLON Y CIPRES I I', 'ISIDRO FABELA PRIMERA SECCION', 'ISIDRO FABELA SEGUNDA SECCION', 'RANCHO DOLORES'],
    "DEL PARQUE": ['DEL PARQUE   I', 'DEL PARQUE  I I', 'LAZARO CARDENAS', 'AMPLIACION LAZARO CARDENAS', 'AZTECA'],
    "INDEPENDENCIA": ['REFORMA Y FERROCARRILES NACIONALES (SAN JUAN BAUTISTA)', 'METEORO', 'INDEPENDENCIA', 'LAS TORRES (CIENTIFICOS)', 'SAN JUAN BUENAVISTA'],
    "LA MAQUINITA": ['RANCHO LA MORA', 'LOS ANGELES', 'CARLOS HANK Y LOS FRAILES', 'GUADALUPE, CLUB JARDIN Y LA MAGDALENA', 'TLACOPA'],
    "METROPOLITANA": ['LAS PALOMAS', 'LAS MARGARITAS', 'RANCHO MAYA'],
    "MODERNA DE LA CRUZ": ['MODERNA DE LA CRUZ  I', 'MODERNA DE LA CRUZ  I I', 'BOSQUES DE COLON'],
    "MORELOS": ['MORELOS 1A SECCION', 'MORELOS 2A SECCION', 'FEDERAL ADOLFO LOPEZ MATEOS'],
    "NUEVA OXTOTITLAN": ['NUEVA OXTOTITLAN  I', 'NUEVA OXTOTITLAN I I'],
    "OCHO CEDROS": ['OCHO CEDROS  I', 'VILLA HOGAR', 'OCHO CEDROS  I I', '8 CEDROS SEGUNDA SECCION'],
    "SAN ANDRES CUEXCONTITLAN": ['SAN ANDRES', 'LA CONCEPCION', 'SANTA ROSA', 'LA NATIVIDAD', 'EJIDO SAN DIEGO DE LOS PADRES', 'SAN DIEGO DE LOS PADRES I', 'SAN DIEGO DE LOS PADRES I I', 'JICALTEPEC  CUEXCONTITLAN', 'LOMA LA PROVIDENCIA', 'EJIDO DE LA Y', 'LA LOMA CUEXCONTITLAN'],
    "SAN ANTONIO BUENAVISTA": ['CAMINO REAL', 'JOSE MARIA HEREDIA', 'LOS ROSALES'],
    "SAN BUENAVENTURA": ['INSURGENTES', 'PENSADOR MEXICANO', 'ALAMEDA 2000', 'CULTURAL', 'DEL DEPORTE', 'GUADALUPE'],
    "SAN CAYETANO DE MORELOS": ['SAN CAYETANO', 'CERRILLO PIEDRAS BLANCAS'],
    "SAN CRISTOBAL HUICHOCHITLAN": ['SAN GABRIEL', 'SAN JOSE GUADALUPE HUICHOCHITLAN', 'LA CONCEPCION', 'LA TRINIDAD  I', 'LA TRINIDAD  I I', 'SAN SALVADOR I I', 'SAN SALVADOR  I'],
    "SAN FELIPE TLALMIMILOLPAN": ['CENTRO', 'EL CALVARIO', 'JARDINES DE SAN PEDRO', 'LA CURVA', 'LOS ALAMOS', 'LA vENTA', 'EL FRONTON', 'DEL PANTEON'],
    "SAN JUAN TILAPA": ['CENTRO', 'LAZARO CARDENAS', 'EL DURAZNO', 'GUADALUPE'],
    "SAN LORENZO TEPALTITLAN": ['CENTRO', 'LAS FLORES', 'EL CHARCO', 'SAN ANGELIN', 'LA CRUZ COMALCO', 'SAN ISIDRO', 'DEL PANTEON', 'RINCON DE SAN LORENZO', 'LA LOMA', 'CELANESE', 'EL MOGOTE'],
    "SAN MARCOS YACHIHUACALTEPEC": ['NORTE', 'SUR'],
    "SAN MARTIN TOLTEPEC": ['SAN MARTIN', 'PASEOS DE SAN MARTIN ( NO MUNICIPAL)', 'SAN ISIDRO', 'LA PALMA TOLTEPEC', 'SEBASTIAN LERDO DE TEJADA', 'EJIDO DE SAN MARCOS YACHIHUACALTEPEC'],
    "SAN MATEO OTZACATIPAN": ['PONIENTE   I', 'PONIENTE  I I', 'RANCHO SAN JOSE', 'CANALEJA', 'ORIENTE  I', 'ORIENTE  I I', 'LA MAGDALENA OTZACATIPAN', 'SANTA CRUZ OTZACATIPAN', 'SAN JOSE GUADALUPE OTZACATIPAN', 'SAN DIEGO DE LOS PADRES OTZACATIPAN', 'SAN BLAS OTZACATIPAN', 'SAN NICOLAS TOLENTINO  I', 'SAN NICOLAS TOLENTINO I I', 'LA CRESPA', 'JARDINES DE LA CRESPA', 'GEOVILLAS ARBOLEDA', 'LA FLORESTA', 'GEOVILLAS DE LA INDEPENDENCIA', 'VICENTE LOMBARDO', 'ARBOLEDAS'],
    "SAN MATEO OXTOTITLAN": ['CENTRO', 'TLALNEPANTLA', 'ATOTONILCO', 'RINCON DEL PARQUE', 'NIÑOS HEROES I', 'NIÑOS HEROES  I I', 'TIERRA Y LIBERTAD', 'PROTIMBOS', '20 DE NOVIEMBRE', '14 DE DICIEMBRE', 'EL TRIGO', 'SAN JORGE'],
    "SAN PABLO AUTOPAN": ['DE JESUS 1A  SECCION', 'STA MARIA TLACHALOYITA', 'PUEBLO NUEVO  I', 'PUEBLO NUEVO  I I', 'SANTA CRUZ  I', 'SANTA CRUZ  I I', 'DE JESUS 3A SECCION', 'DE JESUS 2A SECCION', 'OJO DE AGUA', 'AVIACION AUTOPAN', 'SAN CARLOS AUTOPAN (BARRIO CONTRACAJA)', 'SAN DIEGO LINARES', 'SAN DIEGO', 'REAL DE SAN PABLO', 'XICALTEPEC   B EL CAJON', 'GALAXIA TOLUCA (NO MUNICIPALIZADO)', 'JICALTEPEC AUTOPAN'],
    "SAN PEDRO TOTOLTEPEC": ['DEL CENTRO', 'MANZANA SUR', 'DEL PANTEON', 'GEOVILLAS', 'FRANCISCO I. MADERO', 'LA GALIA', 'NUEVA SAN FRANCISCO', 'SAN MIGUEL TOTOLTEPEC', 'BORDO DE LAS CANASTAS', 'SAN FRANCISCO TOTOLTEPEC', 'GUADALUPE TOTOLTEPEC', 'SAN BLAS TOTOLTEPEC', 'LA CONSTITUCION TOTOLTEPEC', 'ARROYO VISTA HERMOSA'],
    "SAN SEBASTIAN": ['VALLE VERDE Y TERMINAL', 'PROGRESO', 'IZCALLI IPIEM', 'SAN SEBASTIAN Y VERTICE', 'IZCALLI TOLUCA', 'SALVADOR SANCHEZ COLIN', 'COMISION FEDERAL DE ELECTRICIDAD', 'VALLE DON CAMILO'],
    "SANCHEZ": ['SOR JUANA INES DE LA CRUZ', 'ELECTRICISTAS LOCALES', 'LA TERESONA I', 'LA TERESONA  I I', 'LA TERESONA   I I I', 'SECTOR POPULAR'],
    "SANTA ANA TLAPALTITLAN": ['16 DE SEPTIEMBRE', 'PINO SUAREZ', 'DEL PANTEON', 'INDEPENDENCIA', 'SANTA MARIA SUR', 'SANTA MARIA NORTE', 'BUENAVISTA'],
    "SANTA CRUZ ATZCAPOTZALTONGO": ['SANTA CRUZ SUR', 'SANTA CRUZ NORTE', 'EX HACIENDA LA MAGDALENA'],
    "SANTA MARIA DE LAS ROSAS": ['SANTA MARIA DE LAS ROSAS', 'NUEVA SANTA MARIA DE LAS ROSAS', 'UNIDAD VICTORIA', 'LA MAGDALENA', 'NUEVA SANTA MARIA', 'BENITO JUAREZ', 'EVA SAMANO DE LOPEZ MATEOS', 'EMILIANO ZAPATA'],
    "SANTA MARIA TOTOLTEPEC": ['CENTRO', 'EL COECILLO', 'HEROES', 'PASEO TOTOLTEPEC', 'EL OLIMPO', 'EL CARMEN TOTOLTEPEC'],
    "SANTIAGO MILTEPEC": ['MILTEPEC CENTRO', 'MILTEPEC SUR', 'MILTEPEC NORTE'],
    "SANTIAGO TLACOTEPEC": ['DEL CENTRO', 'SANTA MARIA', 'SHINGADE', 'CRISTO REY', 'EL CALVARIO', 'SANTA JUANITA', 'EL REFUGIO'],
    "SANTIAGO TLAXOMULCO": ['EL CALVARIO', 'LA PEÑA', 'JUNTA LOCAL DE CAMINOS'],
    "SAUCES": ['SAUCES  I', 'SAUCES  I I I', 'SAUCES   IV', 'SAUCES  V I', 'SAUCES  V', 'VILLAS SANTIN I', 'VILLAS SANTIN II', 'FRANCISCO VILLA', 'SAUCES II'],
    "SEMINARIO 2 DE MARZO": ['SEMINARIO 4A SECCION  I', 'SEMINARIO 4A SECCION I I', 'HEROES 5 DE MAYO I', 'HEROES 5 DE MAYO I I'],
    "SEMINARIO CONCILIAR": ['SEMINARIO EL PARQUE', 'SEMINARIO 3A. SECCION', 'SEMINARIO 1A. SECCION', 'SEMINARIO EL MODULO'],
    "SEMINARIO LAS TORRES": ['SEMINARIO SAN FELIPE DE JESUS', 'SEMINARIO 2A. SECCION', 'SEMINARIO 5A. SECCION'],
    "TECAXIC": ['TECAXIC ORIENTE', 'TECAXIC PONIENTE'],
    "TLACHALOYA": ['TLACHALOYA', 'BALBUENA', 'SAN CARLOS', 'SAN JOSE BUENAVISTA', 'DEL CENTRO', 'EL TEJOCOTE', 'SAN JOSE LA COSTA'],
    "UNIVERSIDAD": ['UNIVERSIDAD', 'CUAUHTEMOC', 'AMERICAS', 'ALTAMIRANO'],
}

# MAPA INVERSO PARA FUNCIONAMIENTO ÓPTIMO
MAPA_UTB_DEL = {utb: dl for dl, lista in CATALOGO_MAESTRO.items() for utb in lista}

# --- 2. MOTOR LÓGICO MEJORADO ---
def get_real_route(coords_list):
    """Obtiene el trazo vial real desde OSRM con manejo de errores Senior."""
    locs = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
    url = f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5) 
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == 'Ok':
                return data['routes'][0]['geometry']['coordinates'], data['routes'][0]['distance'] / 1000
        return None, None
    except Exception: 
        return None, None

def normalizar_texto(texto):
    if not isinstance(texto, str): texto = str(texto)
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

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
@st.cache_data
def load_massive_data(file, extension):
    # 1. Leemos el archivo
    df = pd.read_excel(file, engine='openpyxl') if extension == 'xlsx' else pd.read_csv(file)
    
    # 2. EL PARCHE: Eliminamos de inmediato filas que estén totalmente vacías
    df = df.dropna(how='all').reset_index(drop=True)
    
    # 3. CORTE QUIRÚRGICO: Si la primera columna (Folio/Fecha) está vacía, dejamos de leer.
    # Esto es lo que elimina el retraso de las 27,000 filas.
    df = df[df.iloc[:, 0].astype(str).str.strip() != "nan"]
    df = df[df.iloc[:, 0].astype(str).str.strip() != ""]
    df = df[df.iloc[:, 0].notna()]

    # 4. Procesamos solo las columnas de Delegación y UTB que tienen datos reales
    df['del_norm'] = df.iloc[:, 22].astype(str).apply(normalizar_texto)
    df['utb_norm'] = df.iloc[:, 23].astype(str).apply(normalizar_texto)
    
    return df
# --- 3. AUTENTICACIÓN Y ESTADO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = False, None, ""
if "menu" not in st.session_state:
    st.session_state.menu = "Inicio"
# Estados para el módulo SF2
if "lista_bajas" not in st.session_state:
    st.session_state.lista_bajas = {} # {folio: comentario}

# --- MEJORA PREMIUM: LLAVES PARA LIMPIEZA DE INPUTS ---
if "input_key" not in st.session_state:
    st.session_state.input_key = 0

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
            st.error("Acceso denegado")
else:
  # --- 4. SIDEBAR (Navegación Personalizada SF) ---
# --- 4. SIDEBAR (Navegación v11.6 - Mantenimiento Total) ---
    with st.sidebar:
        st.title("⚙️ Panel Operativo")
        st.write(f"**Usuario:** {st.session_state.usuario_nombre}")
        st.write("---")
        
        # Seguridad: GuaDAP solo ve SF2-BAJAS
        if st.session_state.perfil == "CONSULTA":
            opciones_menu = {"📖 SF2-BAJAS": "SF2"}
            if st.session_state.menu not in ["SF2", "Inicio"]: st.session_state.menu = "SF2"
        else:
            opciones_menu = {
                "🏠 Inicio": "Inicio",
                "🚀 SF1-GENERADOR DE RUTAS": "GdR",
                "📖 SF2-BAJAS": "SF2",
                "📝 SF3-CAPTURA": "SF3",
                "📐 SF4-DISEÑO DE PROCESOS": "SF4"
            }
        
        for label, target in opciones_menu.items():
            if st.button(label, use_container_width=True, type="primary" if st.session_state.menu == target else "secondary"):
                st.session_state.menu = target
                st.rerun()

        st.write("---")
        # Recuperación de Sliders para el Administrador
        if st.session_state.menu == "GdR" and st.session_state.perfil == "ADMIN":
            st.subheader("📊 Ajustes SF1")
            t_por_punto = st.slider("Minutos por Atención", 5, 60, 20)
            v_promedio = st.slider("Velocidad km/h", 10, 80, 25)
            st.write("---")

        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
        st.info("SF PANGEA V1")

    # --- 5. CUERPO LÓGICO (FUNCIONALIDAD ÍNTEGRA DE TU 11.5) ---
    if st.session_state.menu == "Inicio":
        st.title("👋 Bienvenido a SF PANGEA")
        st.info("Sistema de Gestión Operativa - Dirección de Alumbrado Público")
        st.image("https://img.icons8.com/clouds/500/000000/map-marker.png", width=150)

    elif st.session_state.menu == "GdR":
        st.title("🚀 SF1-GENERADOR DE RUTAS")
        tab1, tab2, tab3 = st.tabs(["🆕 Nueva Ruta", "📂 Bitácora", "🗑️ Papelera"])
        
        with tab1:
            up = st.file_uploader("Subir Archivo (Excel/CSV)", type=["csv", "xlsx"])
            if up:
                try:
                    df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
                    id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                    res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                    df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
                    df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)
                    
                    if not df_v.empty:
                        pts = df_v.to_dict('records'); ordenados_temp = []; last_coord = BASE_COORDS
                        while pts:
                            rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                            idx = np.argmin(cdist([last_coord], rest))
                            proximo = pts.pop(idx); ordenados_temp.append(proximo); last_coord = (proximo['lat_aux'], proximo['lon_aux'])
                        
                        ordenados = ordenados_temp[::-1] # Lógica punto lejano primero
                        route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                        geo_trazo, dist_real_km = get_real_route(route_coords) # Motor OSRM
                        
                        total_lums = total_postes = total_cable = 0
                        for i, p in enumerate(ordenados, 1):
                            p['No_Ruta'], p['ID_Pangea_Nombre'] = i, p[id_col]
                            p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 and extraer_carga_robusta(p, 'cable')==0 else 0)
                            p['Cant_Postes'], p['Cant_Cable_m'] = extraer_carga_robusta(p, 'poste'), extraer_carga_robusta(p, 'cable')
                            p['Maps'] = f"https://www.google.com/maps?q={p['lat_aux']},{p['lon_aux']}"
                            total_lums += p['Cant_Luminarias']; total_postes += p['Cant_Postes']; total_cable += p['Cant_Cable_m']
                        
                        min_totales = ((total_lums + total_postes) * t_por_punto) + (dist_real_km / v_promedio * 60)
                        tiempo_abreviado = f"{int(min_totales // 60)} h {int(min_totales % 60)} m"

                        st.subheader("📊 Resumen Operativo")
                        m1, m2, m3, m4, m5, m6 = st.columns(6)
                        m1.metric("📍 Puntos", len(ordenados)); m2.metric("💡 Luminarias", total_lums)
                        m3.metric("🏗️ Postes", total_postes); m4.metric("🧶 Cable", f"{total_cable}m")
                        m5.metric("🛣️ KM", round(dist_real_km,2)); m6.metric("⏱️ Tiempo Est.", tiempo_abreviado)

                        df_export = pd.DataFrame(ordenados)
                        st.dataframe(df_export[['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']], use_container_width=True)
                        
                        c1, c2, c3, c4 = st.columns(4)
                        # Recuperación de Excel con Colores (Gris/Azul) y Resumen Dinámico
                        buf_xlsx = io.BytesIO()
                        with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
                            df_export.to_excel(writer, index=False, sheet_name='Ruta')
                            ws = writer.sheets['Ruta']; last_r = len(ordenados)+1; res_r = last_r+2
                            ws.cell(row=res_r, column=2, value="--- RESUMEN DINÁMICO ---")
                            ws.cell(row=res_r+1, column=1, value="Total Lums:"); ws.cell(row=res_r+1, column=2, value=total_lums)
                            fg, fa = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid"), PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
                            for r in range(2, last_r + 1):
                                if int(df_export.iloc[r-2]['Cant_Postes']) > 0:
                                    for cell in ws[r]: cell.fill = fg
                                elif int(df_export.iloc[r-2]['Cant_Cable_m']) > 0:
                                    for cell in ws[r]: cell.fill = fa
                        c1.download_button("📗 Excel Pro", buf_xlsx.getvalue(), f"SF1_{up.name}.xlsx", use_container_width=True)
                        
                        kml = simplekml.Kml()
                        if geo_trazo:
                            ls = kml.newlinestring(name="Trayecto Vial", coords=[(float(c[0]), float(c[1])) for c in geo_trazo])
                            ls.style.linestyle.width = 6; ls.style.linestyle.color = 'ff0000ff'
                        for p in ordenados:
                            pnt = kml.newpoint(name=str(p[id_col]), coords=[(p['lon_aux'], p['lat_aux'])])
                            pnt.description = f"Punto: {p['No_Ruta']}\nLums: {p['Cant_Luminarias']}"
                        c2.download_button("🗺️ KML Maestro", kml.kml(), f"SF1_{up.name}.kml", use_container_width=True)
                except Exception as e: st.error(f"Error: {e}")

    elif st.session_state.menu == "SF2":
        st.title("📖 SF2-BAJAS")
        # Aquí va todo tu código de Bajas (líneas 374 a 455 de tu 11.5)
        # (Lo omito en este mensaje para no confundirte, pero NO lo borres de tu archivo)

    elif st.session_state.menu == "SF3":
        st.title("📝 SF3-CAPTURA")
        # Aquí va todo tu código de Captura/Carta (líneas 173 a 370 de tu 11.5)
        # (Lo omito en este mensaje para no confundirte, pero NO lo borres de tu archivo)

    elif st.session_state.menu == "SF4":
        st.title("📐 SF4-DISEÑO DE PROCESOS")
        st.info("Módulo de Organización y Métodos - Dirección de Alumbrado Público")
            except: st.info("Cargando papelera...")

    elif st.session_state.menu == "SF2":
        st.title("📖 SF2-BAJAS")
        up_sf2 = st.file_uploader("Archivo Referencia", type=["csv", "xlsx"])
        if up_sf2:
            try:
                df_ref = pd.read_excel(up_sf2, dtype=str).fillna("") if up_sf2.name.endswith('.xlsx') else pd.read_csv(up_sf2, encoding='latin-1', dtype=str).fillna("")
                id_col_sf2 = next((c for c in df_ref.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID','IMEI'])), df_ref.columns[0])
                c1, c2 = st.columns(2)
                with c1:
                    with st.form("f_b", clear_on_submit=True):
                        f_i = st.text_input("Folio/Ticket/IMEi:"); r_i = st.text_input("Respuesta:", max_chars=30)
                        if st.form_submit_button("➕ Agregar"):
                            if f_i.strip() in df_ref[id_col_sf2].astype(str).values:
                                st.session_state.lista_bajas[f_i.strip()] = r_i.strip() or "ATENDIDO"; st.rerun()
                            else: st.error("Folio no existe")
                    if st.button("🗑️ Limpiar"): st.session_state.lista_bajas = {}; st.rerun()
                with c2:
                    if st.session_state.lista_bajas:
                        df_res = pd.DataFrame([{"Folio": k, "Respuesta": v} for k, v in st.session_state.lista_bajas.items()])
                        st.dataframe(df_res, use_container_width=True)
                        if st.button("📥 Generar Documento"):
                            df_f = df_ref[df_ref[id_col_sf2].astype(str).isin(list(st.session_state.lista_bajas.keys()))].copy()
                            df_f['RESPUESTA 127'] = df_f[id_col_sf2].map(st.session_state.lista_bajas)
                            out = io.BytesIO()
                            with pd.ExcelWriter(out, engine='openpyxl') as w: df_f.to_excel(w, index=False)
                            st.download_button("📗 Descargar Excel", out.getvalue(), f"BAJAS_{up_sf2.name}.xlsx", use_container_width=True)
            except Exception as e: st.error(f"Error: {e}")

    elif st.session_state.menu == "SF3":
        st.title("📝 SF3-CAPTURA")
        with st.expander("📝 FORMULARIO DE CAPTURA", expanded=True):
            with st.form("c_sf3", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                f_f = c1.date_input("Fecha"); f_o = c2.text_input("O.T."); f_c = c3.text_input("Calle")
                c4, c5, c6 = st.columns(3)
                f_d = c4.selectbox("Delegación", sorted(list(CATALOGO_MAESTRO.keys())))
                f_u = c5.selectbox("UTB", sorted(CATALOGO_MAESTRO.get(f_d, [])))
                f_fol = c6.text_input("Folio/Ticket")
                m1, m2, m3, m4 = st.columns(4)
                r, m, s, a = m1.number_input("Rehab",0), m2.number_input("Manto",0), m3.number_input("Sust",0), m4.number_input("Ampli",0)
                obs = st.text_area("Observaciones")
                if st.form_submit_button("🚀 GUARDAR"):
                    if "manual_db" not in st.session_state: st.session_state.manual_db = []
                    st.session_state.manual_db.append({"FECHA":f_f.strftime("%d/%m/%Y"),"OT":f_o.upper(),"CALLE":f_c.upper(),"DELEGACIÓN":f_d,"UTB":f_u,"FOLIO":f_fol.upper(),"REHAB":r,"MANTO":m,"SUST":s,"AMPLI":a,"OBS":obs})
                    st.rerun()

    elif st.session_state.menu == "SF4":
        st.title("📐 SF4-DISEÑO DE PROCESOS")
        st.info("Módulo de Organización y Métodos - Dirección de Alumbrado Público")
