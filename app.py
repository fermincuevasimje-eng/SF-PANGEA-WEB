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
    d_letras = {'un ':'1 ','uno ':'1 ','una ':'1 ','dos ':'2 ','tres ':'3 ','cuatro ':'4 ','cinco ':'5 '}
    posibles_cols = ['ASUNTO', 'Observaciones', 'asunto', 'observaciones']
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
        if any(w in t_norm for w in ['cable', 'conductor', 'linea']):
            m_flex = re.search(r'(\d+)\s*(?:metro|m)s?', t_norm)
            return int(m_flex.group(1)) if m_flex else 0
        return 0
    m = re.search(patrones[tipo], t_norm)
    return int(m.group(1)) if m else 0

@st.cache_data
def load_massive_data(file, extension):
    df = pd.read_excel(file, engine='openpyxl') if extension == 'xlsx' else pd.read_csv(file)
    df = df.dropna(how='all').reset_index(drop=True)
    df = df[df.iloc[:, 0].astype(str).str.strip() != "nan"]
    df['del_norm'] = df.iloc[:, 22].astype(str).apply(normalizar_texto)
    df['utb_norm'] = df.iloc[:, 23].astype(str).apply(normalizar_texto)
    return df

# --- 3. AUTENTICACIÓN Y ESTADO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = False, None, ""
if "menu" not in st.session_state:
    st.session_state.menu = "Inicio"
if "lista_bajas" not in st.session_state: st.session_state.lista_bajas = {}
if "input_key" not in st.session_state: st.session_state.input_key = 0

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
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("⚙️ Panel Operativo")
        st.write(f"**Usuario:** {st.session_state.usuario_nombre}")
        st.write("---")
        if st.button("🏠 Inicio", use_container_width=True): st.session_state.menu = "Inicio"
        if st.button("🚀 SF1-Generador de Rutas", use_container_width=True): st.session_state.menu = "SF1"
        if st.button("📁 SF2-Bajas", use_container_width=True): st.session_state.menu = "SF2"
        if st.button("📊 SF3-Captura y Métricas", use_container_width=True): st.session_state.menu = "SF3"
        if st.button("🏗️ SF4-Diseño de Procesos", use_container_width=True): st.session_state.menu = "SF4"
        st.write("---")
        if st.session_state.menu == "SF1":
            st.subheader("📊 Ajustes GdR")
            t_por_punto = st.slider("Minutos por Atención", 5, 60, 20)
            v_promedio = st.slider("Velocidad km/h", 10, 80, 25)
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()

    # --- 5. CUERPO LÓGICO ---
    if st.session_state.menu == "Inicio":
        st.title("👋 Bienvenido a SF PANGEA")
        st.info("Sistema de Gestión Operativa - Dirección de Alumbrado Público")
        st.image("https://img.icons8.com/clouds/500/000000/map-marker.png", width=150)

    elif st.session_state.menu == "SF3":
        st.title(f"🛠️ Módulo SF3 - Gestión y Métricas")
        if "manual_db" not in st.session_state: st.session_state.manual_db = []
        if "masivo_persistente" not in st.session_state: st.session_state.masivo_persistente = None
        if "reset_key" not in st.session_state: st.session_state.reset_key = 0
        rk = st.session_state.reset_key

        with st.expander("📝 REGISTRAR NUEVA ATENCIÓN (FORMULARIO)", expanded=False):
            with st.form(key=f"form_sf3_v14_final_{rk}", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1: f_fecha = st.date_input("1. Fecha de Atención")
                with c2: f_ot = st.text_input("2. O.T.")
                c3, c4 = st.columns(2)
                with c3: f_folio = st.text_input("3. Folio / Ticket / IMEI")
                with c4: f_calle = st.text_input("4. Calle")
                c_sel1, c_sel2 = st.columns(2)
                with c_sel1: f_del = st.selectbox("📍 5. Delegación", sorted(list(CATALOGO_MAESTRO.keys())))
                with c_sel2:
                    opciones_utb_f = sorted(CATALOGO_MAESTRO.get(f_del, []))
                    f_utb = st.selectbox("🔍 6. UTB", opciones_utb_f)
                st.markdown("---")
                m1, m2, m3, m4 = st.columns(4)
                with m1: f_rehab = st.number_input("7. Rehabilitación", min_value=0, step=1)
                with m2: f_manto = st.number_input("8. Mantenimiento", min_value=0, step=1)
                with m3: f_sust = st.number_input("9. Sustitución", min_value=0, step=1)
                with m4: f_ampli = st.number_input("10. Ampliación", min_value=0, step=1)
                f_obs = st.text_area("11. Observaciones")
                if st.form_submit_button("🚀 GUARDAR REGISTRO MANUAL", use_container_width=True):
                    st.session_state.manual_db.append({
                        "FECHA": f_fecha.strftime("%d/%m/%Y"), "OT": f_ot.upper(), "FOLIO": f_folio.upper(),
                        "CALLE": f_calle.upper(), "DELEGACIÓN": f_del, "UTB": f_utb, "REHAB": f_rehab,
                        "MANTO": f_manto, "SUST": f_sust, "AMPLI": f_ampli, "OBS": f_obs
                    })
                    st.session_state.reset_key += 1
                    st.toast("Guardado correctamente"); time.sleep(0.5); st.rerun()

        if st.session_state.manual_db and st.button("🗑️ Borrar Último Manual"):
            st.session_state.manual_db.pop(); st.rerun()

        st.markdown("---")
        up_cap = st.file_uploader("📂 Cargar Archivo Masivo", type=["csv", "xlsx"])
        if up_cap:
            ext = 'xlsx' if up_cap.name.endswith('.xlsx') else 'csv'
            st.session_state.masivo_persistente = load_massive_data(up_cap, ext)
            st.success("Archivo anclado a memoria.")
        
        if st.session_state.masivo_persistente is not None and st.button("❌ Quitar Archivo"):
            st.session_state.masivo_persistente = None; st.rerun()

        total_rehab, total_manto, total_sust, total_ampli = 0, 0, 0, 0
        df_final = pd.DataFrame()

        if st.session_state.manual_db:
            df_man = pd.DataFrame(st.session_state.manual_db)
            total_rehab += df_man["REHAB"].sum(); total_manto += df_man["MANTO"].sum()
            total_sust += df_man["SUST"].sum(); total_ampli += df_man["AMPLI"].sum()
            df_final = df_man.copy()

        if st.session_state.masivo_persistente is not None:
            df_c = st.session_state.masivo_persistente
            c_f1, c_f2 = st.columns(2)
            with c_f1: s_del = st.selectbox("📍 Filtrar Masivo:", ["TODAS"] + sorted(list(CATALOGO_MAESTRO.keys())))
            with c_f2:
                opts_utb = ["TODAS"] + (sorted(CATALOGO_MAESTRO.get(s_del, [])) if s_del != "TODAS" else sorted(list(MAPA_UTB_DEL.keys())))
                s_utb = st.selectbox("🔍 UTB Masivo:", opts_utb)
            
            df_f_mas = df_c.copy()
            if s_del != "TODAS": df_f_mas = df_f_mas[df_f_mas['del_norm'] == normalizar_texto(s_del)]
            if s_utb != "TODAS": df_f_mas = df_f_mas[df_f_mas['utb_norm'] == normalizar_texto(s_utb)]

            total_rehab += pd.to_numeric(df_f_mas.iloc[:, 29], errors='coerce').fillna(0).sum()
            total_manto += pd.to_numeric(df_f_mas.iloc[:, 30], errors='coerce').fillna(0).sum()
            total_sust += pd.to_numeric(df_f_mas.iloc[:, 31], errors='coerce').fillna(0).sum()
            total_ampli += pd.to_numeric(df_f_mas.iloc[:, 39], errors='coerce').fillna(0).sum()

            df_mas_v = df_f_mas.iloc[:, [4, 19, 22, 23, 29, 30, 31, 39]].copy()
            df_mas_v.columns = ["FECHA", "CALLE", "DELEGACIÓN", "UTB", "REHAB", "MANTO", "SUST", "AMPLI"]
            df_mas_v["OT"], df_mas_v["FOLIO"], df_mas_v["OBS"] = "MASIVO", "MASIVO", ""
            df_final = pd.concat([df_final, df_mas_v], ignore_index=True, sort=False)

        st.subheader("📊 Resumen Consolidado")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🔧 Rehab", int(total_rehab)); m2.metric("🧹 Manto", int(total_manto))
        m3.metric("💡 Sust", int(total_sust)); m4.metric("➕ Ampli", int(total_ampli))

        if not df_final.empty:
            ord_cols = ["FECHA", "OT", "FOLIO", "CALLE", "DELEGACIÓN", "UTB", "REHAB", "MANTO", "SUST", "AMPLI", "OBS"]
            st.dataframe(df_final[ord_cols], use_container_width=True, hide_index=True)

    elif st.session_state.menu == "SF2":
        st.title("📁 SF2 - Bajas")
        up_sf2 = st.file_uploader("Subir Archivo de Referencia", type=["csv", "xlsx"], key="sf2_up")
        if up_sf2:
            try:
                df_ref = pd.read_excel(up_sf2, dtype=str).fillna("") if up_sf2.name.endswith('.xlsx') else pd.read_csv(up_sf2, encoding='latin-1', dtype=str).fillna("")
                id_col = next((c for c in df_ref.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_ref.columns[0])
                c_in, c_ls = st.columns(2)
                with c_in:
                    with st.form("form_bajas", clear_on_submit=True):
                        f_v = st.text_input("Folio:"); r_v = st.text_input("Respuesta (ATENDIDO):")
                        if st.form_submit_button("➕ Agregar"):
                            if f_v.strip() in df_ref[id_col].values:
                                st.session_state.lista_bajas[f_v.strip()] = r_v.strip() or "ATENDIDO"
                                st.rerun()
                            else: st.error("No existe.")
                    if st.button("🗑️ Limpiar"): st.session_state.lista_bajas = {}; st.rerun()
                with c_ls:
                    if st.session_state.lista_bajas:
                        st.write(pd.DataFrame([{"Folio": k, "R": v} for k, v in st.session_state.lista_bajas.items()]))
                        if st.button("📥 Generar Excel"):
                            df_b = df_ref[df_ref[id_col].isin(st.session_state.lista_bajas.keys())].copy()
                            df_b['RESPUESTA 127'] = df_b[id_col].map(st.session_state.lista_bajas)
                            buf = io.BytesIO()
                            with pd.ExcelWriter(buf, engine='openpyxl') as w: df_b.to_excel(w, index=False)
                            st.download_button("Descargar", buf.getvalue(), "BAJAS.xlsx")
            except Exception as e: st.error(e)

    elif st.session_state.menu == "SF1":
        st.title("🚀 SF1 - Rutas")
        up = st.file_uploader("Archivo Rutas", type=["csv", "xlsx"])
        if up:
            try:
                df_r = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
                id_c = next((c for c in df_r.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_r.columns[0])
                res = df_r.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                df_r['lat'], df_r['lon'] = res.apply(lambda x: float(x.group(1)) if x else None), res.apply(lambda x: float(x.group(2)) if x else None)
                df_v = df_r.dropna(subset=['lat']).reset_index(drop=True)
                if not df_v.empty:
                    pts = df_v.to_dict('records')
                    ord_p, last = [], BASE_COORDS
                    while pts:
                        idx = np.argmin(cdist([last], [[p['lat'], p['lon']] for p in pts]))
                        p = pts.pop(idx); ord_p.append(p); last = (p['lat'], p['lon'])
                    ord_p = ord_p[::-1]
                    for i, p in enumerate(ord_p, 1): p['No_Ruta'] = i
                    st.success("Ruta optimizada."); st.dataframe(pd.DataFrame(ord_p)[[ 'No_Ruta', id_c]])
                    kml = simplekml.Kml()
                    for p in ord_p: kml.newpoint(name=p[id_c], coords=[(p['lon'], p['lat'])])
                    st.download_button("🗺️ KML", kml.kml(), "RUTA.kml")
            except Exception as e: st.error(e)

    elif st.session_state.menu == "SF4":
        st.title("🏗️ SF4 - Diseño")
        st.info("Módulo de Diseño de Procesos en construcción.")
