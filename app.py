import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time, random
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

# --- 1. CONFIGURACIÓN E INTERFAZ ---
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

# --- 1.5 CATÁLOGO MAESTRO ---
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

MAPA_UTB_DEL = {utb: dl for dl, lista in CATALOGO_MAESTRO.items() for utb in lista}

# --- 2. MOTOR LÓGICO ---
def get_real_route(coords_list):
    locs = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
    url = f"http://router.project-osrm.org/route/v1/driving/{locs}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5) 
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == 'Ok':
                return data['routes'][0]['geometry']['coordinates'], data['routes'][0]['distance'] / 1000
        return None, None
    except: return None, None

def normalizar_texto(texto):
    if not isinstance(texto, str): texto = str(texto)
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def extraer_carga_robusta(punto_dict, tipo):
    patrones = {
        'lum': r'(\d+)\s*(?:lampara|foco|reflector|arbotante|luminari[oa]|unidad|brazo|farol[a]?|punto de luz)s?',
        'poste': r'(\d+)\s*(?:poste|estructura|columna)s?',
        'cable': r'(\d+)\s*(?:metro|m)\.?\s*(?:de\s*)?(?:cable|conductor|linea|red|alambre|potencia)s?'
    }
    texto = str(punto_dict.get('Asunto', '')).lower() + " " + str(punto_dict.get('Observaciones', '')).lower()
    m = re.search(patrones[tipo], texto)
    return int(m.group(1)) if m else 0

@st.cache_data
def load_massive_data(file, extension):
    df = pd.read_excel(file, engine='openpyxl') if extension == 'xlsx' else pd.read_csv(file)
    df = df.dropna(how='all').reset_index(drop=True)
    df = df[df.iloc[:, 0].notna()]
    df['del_norm'] = df.iloc[:, 22].astype(str).apply(normalizar_texto)
    df['utb_norm'] = df.iloc[:, 23].astype(str).apply(normalizar_texto)
    return df

# --- 3. AUTENTICACIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = False, None, ""
if "menu" not in st.session_state: st.session_state.menu = "Inicio"
if "lista_bajas" not in st.session_state: st.session_state.lista_bajas = {}
if "manual_db" not in st.session_state: st.session_state.manual_db = []

if not st.session_state.autenticado:
    st.title("🔐 Acceso SF PANGEA")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
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
        
        if st.session_state.perfil == "CONSULTA":
            opciones = {"🚀 SF1-GENERADOR DE RUTAS": "GdR", "📖 SF2-BAJAS": "SF2"}
            if st.session_state.menu not in ["GdR", "SF2", "Inicio"]: st.session_state.menu = "SF2"
        else:
            opciones = {
                "🏠 Inicio": "Inicio",
                "🚀 SF1-GENERADOR DE RUTAS": "GdR",
                "📖 SF2-BAJAS": "SF2",
                "📝 SF3-CAPTURA": "SF3",
                "📐 SF4-DISEÑO DE PROCESOS": "SF4"
            }
        
        for label, target in opciones.items():
            if st.button(label, use_container_width=True, type="primary" if st.session_state.menu == target else "secondary"):
                st.session_state.menu = target
                st.rerun()

        if st.session_state.menu == "GdR" and st.session_state.perfil == "ADMIN":
            t_por_punto = st.slider("Minutos por Atención", 5, 60, 20)
            v_promedio = st.slider("Velocidad km/h", 10, 80, 25)

        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()

    # --- 5. CUERPO LÓGICO ---
    if st.session_state.menu == "Inicio":
        st.title("👋 Bienvenido")
        st.info("Sistema de Gestión Operativa - Alumbrado Público")

    elif st.session_state.menu == "GdR":
        st.title("🚀 SF1-GENERADOR DE RUTAS")
        tab1, tab2, tab3 = st.tabs(["🆕 Nueva Ruta", "📂 Bitácora", "🗑️ Papelera"])
        with tab1:
            if st.session_state.perfil == "CONSULTA": st.warning("Modo Consulta")
            else:
                up = st.file_uploader("Subir Archivo", type=["csv", "xlsx"])
                if up:
                    df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
                    id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET'])), df_raw.columns[0])
                    res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                    df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
                    df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)
                    if not df_v.empty:
                        pts = df_v.to_dict('records'); ordenados = []; last_coord = BASE_COORDS
                        while pts:
                            rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                            idx = np.argmin(cdist([last_coord], rest))
                            p_prox = pts.pop(idx); ordenados.append(p_prox); last_coord = (p_prox['lat_aux'], p_prox['lon_aux'])
                        
                        ordenados = ordenados[::-1] # Punto lejano primero
                        route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                        geo_trazo, dist_km = get_real_route(route_coords)
                        
                        total_lums = sum(extraer_carga_robusta(p, 'lum') for p in ordenados)
                        st.subheader("📊 Resumen")
                        st.metric("Puntos", len(ordenados))
                        
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                            pd.DataFrame(ordenados).to_excel(writer, index=False, sheet_name='Ruta')
                            ws = writer.sheets['Ruta']
                            for r in range(2, len(ordenados)+2):
                                ws[r][0].fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
                        st.download_button("📗 Excel Pro", buf.getvalue(), f"SF_{up.name}.xlsx")

        with tab2: # BITÁCORA
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_bt = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                st.dataframe(df_bt, use_container_width=True)
            except: st.info("Sincronizando...")

    elif st.session_state.menu == "SF2":
        st.title("📖 SF2-BAJAS")
        up_sf2 = st.file_uploader("Referencia", type=["csv", "xlsx"])
        if up_sf2:
            st.info("Módulo de Bajas Activo")

    elif st.session_state.menu == "SF3":
        st.title("📝 SF3-CAPTURA")
        with st.form("captura"):
            c1, c2 = st.columns(2)
            f_ot = c1.text_input("O.T.")
            f_del = c2.selectbox("Delegación", sorted(list(CATALOGO_MAESTRO.keys())))
            if st.form_submit_button("Guardar"):
                st.session_state.manual_db.append({"OT": f_ot, "DEL": f_del})
                st.success("Guardado")

    elif st.session_state.menu == "SF4":
        st.title("📐 SF4-DISEÑO DE PROCESOS")
