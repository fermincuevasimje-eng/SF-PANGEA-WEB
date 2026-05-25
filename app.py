import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time, os, json, base64
from streamlit_gsheets import GSheetsConnection
from openpyxl.styles import PatternFill

# --- 1. CONFIGURACIÓN E INTERFAZ (MARCA DE AGUA SF) ---
st.set_page_config(page_title="SF PANGEA V24", layout="wide")

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

# --- 1.5 CATÁLOGO MAESTRO ACTUALIZADO ---
CATALOGO_MAESTRO = {
    "ADOLFO LOPEZ MATEOS": ['PARQUES NACIONALES I', 'MIGUEL HIDALGO  (CORRALITOS)', 'PARQUES NACIONALES  II'],
    "ARBOL DE LAS MANITAS": ['ZOPILOCALCO SUR', 'ZOPILOCALCO NORTE', 'LOMAS ALTAS', 'HUITZILA Y DOCTORES', 'NIÑOS HEROES (PENSIONES)'],
    "BARRIO TRADICIONALES": ['SANTA BARBARA', 'EL COPORO', 'LA RETAMA', 'SAN MIGUEL APINAHUISCO', 'UNION', 'SAN LUIS OBISPO'],
    "CACALOMACAN": ['CENTRO', 'RANCHO SAN MIGUEL ZACANGO', 'SAGRADO CORAZON', 'EL ARENAL'],
    "CALIXTLAHUACA": ['SAN FRANCISCO DE ASIS', 'ZONA ARQUEOLOGICA', 'EL CALVARIO', 'PALMILLAS'],
    "CAPULTITLAN": ['SAN ISIDRO LABRADOR', 'PASEOS DEL  VALLE', 'SAN JUDAS TADEO', 'LA SOLEDAD', 'LOS PINOS', 'GUADALUPE'],
    "CENTRO HISTORICO": ['CENTRO', 'SANTA CLARA', '5 DE MAYO', 'FRANCISCO MURGUIA (EL RANCHITO)', 'LA MERCED ( ALAMEDA)'],
    "CERRILLO VISTA HERMOSA": ['EL CERRILLO', 'EL EMBARCADERO'],
    "CIUDAD UNIVERSITARIA": ['PLAZAS DE SAN BUENAVENTURA', 'SAN BERNARDINO', 'VICENTE GUERRERO'],
    "COLON": ['COLON Y CIPRES I', 'COLON Y CIPRES II', 'ISIDRO FABELA PRIMERA SECCION', 'ISIDRO FABELA SEGUNDA SECCION', 'RANCHO DOLORES'],
    "DEL PARQUE": ['DEL PARQUE   I', 'DEL PARQUE  II', 'LAZARO CARDENAS', 'AMPLIACION LAZARO CARDENAS', 'AZTECA'],
    "INDEPENDENCIA": ['REFORMA Y FERROCARRILES NACIONALES', 'METEORO', 'INDEPENDENCIA', 'LAS TORRES (CIENTIFICOS)', 'SAN JUAN BUENAVISTA'],
    "LA MAQUINITA": ['RANCHO LA MORA', 'LOS ANGELES', 'CARLOS HANK Y LOS FRAILES', 'GUADALUPE, CLUB JARDIN Y LA MAGDALENA', 'TLACOPA'],
    "METROPOLITANA": ['LAS PALOMAS', 'LAS MARGARITAS', 'RANCHO MAYA'],
    "MODERNA DE LA CRUZ": ['MODERNA DE LA CRUZ  I', 'MODERNA DE LA CRUZ  II', 'BOSQUES DE COLON'],
    "MORELOS": ['MORELOS 1A SECCION', 'MORELOS 2A SECCION', 'FEDERAL (ADOLFO LOPEZ MATEOS)'],
    "NUEVA OXTOTITLAN": ['NUEVA OXTOTITLAN  I', 'NUEVA OXTOTITLAN II'],
    "OCHO CEDROS": ['OCHO CEDROS  I', 'VILLA HOGAR', 'OCHO CEDROS  II', '8 CEDROS SEGUNDA SECCION'],
    "SAN ANDRES CUEXCONTITLAN": ['SAN ANDRES', 'LA CONCEPCION', 'SANTA ROSA', 'LA NATIVIDAD', 'EJIDO SAN DIEGO DE LOS PADRES CUEXCONTITLAN', 'SAN DIEGO DE LOS PADRES I', 'SAN DIEGO DE LOS PADRES II', 'JICALTEPEC  CUEXCONTITLAN', 'LOMA LA PROVIDENCIA', 'EJIDO DE LA Y', 'LA LOMA CUEXCONTITLAN'],
    "SAN ANTONIO BUENAVISTA": ['CAMINO REAL', 'JOSE MARIA HEREDIA', 'LOS ROSALES'],
    "SAN BUENAVENTURA": ['INSURGENTES', 'PENSADOR MEXICANO', 'ALAMEDA 2000', 'CULTURAL', 'DEL DEPORTE', 'GUADALUPE'],
    "SAN CAYETANO DE MORELOS": ['SAN CAYETANO', 'CERRILLO PIEDRAS BLANCAS'],
    "SAN CRISTOBAL HUICHOCHITLAN": ['SAN GABRIEL', 'SAN JOSE GUADALUPE HUICHOCHITLAN', 'LA CONCEPCION', 'LA TRINIDAD I', 'LA TRINIDAD II', 'SAN SALVADOR II', 'SAN SALVADOR I'],
    "SAN FELIPE TLALMIMILOLPAN": ['CENTRO', 'EL CALVARIO', 'JARDINES DE SAN PEDRO', 'LA CURVA', 'LOS ALAMOS', 'LA VENTA', 'EL FRONTON', 'DEL PANTEON'],
    "SAN JUAN TILAPA": ['CENTRO', 'LAZARO CARDENAS', 'EL DURAZNO', 'GUADALUPE'],
    "SAN LORENZO TEPALTITLAN": ['CENTRO', 'LAS FLORES', 'EL CHARCO', 'SAN ANGELIN', 'LA CRUZ COMALCO', 'SAN ISIDRO', 'DEL PANTEON', 'RINCON DE SAN LORENZO', 'LA LOMA', 'CELANESE', 'EL MOGOTE'],
    "SAN MARCOS YACHIHUACALTEPEC": ['NORTE', 'SUR'],
    "SAN MARTIN TOLTEPEC": ['SAN MARTIN', 'PASEOS DE SAN MARTIN', 'SAN ISIDRO', 'LA PALMA TOLTEPEC', 'SEBASTIAN LERDO DE TEJADA', 'EJIDO DE SAN MARCOS YACHIHUACALTEPEC'],
    "SAN MATEO OTZACATIPAN": ['PONIENTE   I', 'PONIENTE  I I', 'RANCHO SAN JOSE', 'CANALEJA', 'ORIENTE  I', 'ORIENTE  II', 'LA MAGDALENA OTZACATIPAN', 'SANTA CRUZ OTZACATIPAN', 'SAN JOSE GUADALUPE OTZACATIPAN', 'SAN DIEGO DE LOS PADRES OTZACATIPAN', 'SAN BLAS OTZACATIPAN', 'SAN NICOLAS TOLENTINO I', 'SAN NICOLAS TOLENTINO II', 'LA CRESPA', 'JARDINES DE LA CRESPA', 'GEOVILLAS ARBOLEDA', 'LA FLORESTA', 'GEOVILLAS DE LA INDEPENDENCIA', 'VICENTE LOMBARDO', 'ARBOLEDAS'],
    "SAN MATEO OXTOTITLAN": ['CENTRO', 'TLALNEPANTLA', 'ATOTONILCO', 'RINCON DEL PARQUE', 'NIÑOS HEROES I', 'NIÑOS HEROES  II', 'TIERRA Y LIBERTAD', 'PROTIMBOS', '20 DE NOVIEMBRE', '14 DE DICIEMBRE', 'EL TRIGO', 'SAN JORGE'],
    "SAN PABLO AUTOPAN": ['DE JESUS 1A  SECCION', 'STA MARIA TLACHALOYITA', 'PUEBLO NUEVO  I', 'PUEBLO NUEVO  II', 'SANTA CRUZ  I', 'SANTA CRUZ  II', 'DE JESUS 3A SECCION', 'DE JESUS 2A SECCION', 'OJO DE AGUA', 'AVIACION AUTOPAN', 'SAN CARLOS AUTOPAN', 'SAN DIEGO LINARES', 'SAN DIEGO', 'REAL DE SAN PABLO', 'XICALTEPEC', 'GALAXIA TOLUCA', 'JICALTEPEC AUTOPAN'],
    "SAN PEDRO TOTOLTEPEC": ['DEL CENTRO', 'MANZANA SUR', 'DEL PANTEON', 'GEOVILLAS', 'FRANCISCO I. MADERO', 'LA GALIA', 'NUEVA SAN FRANCISCO', 'SAN MIGUEL TOTOLTEPEC', 'BORDO DE LAS CANASTAS', 'SAN FRANCISCO TOTOLTEPEC', 'GUADALUPE TOTOLTEPEC', 'SAN BLAS TOTOLTEPEC', 'LA CONSTITUCION TOTOLTEPEC', 'ARROYO VISTA HERMOSA'],
    "SAN SEBASTIAN": ['VALLE VERDE Y TERMINAL', 'PROGRESO', 'IZCALLI IPIEM', 'SAN SEBASTIAN Y VERTICE', 'IZCALLI TOLUCA', 'SALVADOR SANCHEZ COLIN', 'COMISION FEDERAL DE ELECTRICIDAD', 'VALLE DON CAMILO'],
    "SANCHEZ": ['SOR JUANA INES DE LA CRUZ', 'ELECTRICISTAS LOCALES', 'LA TERESONA I', 'LA TERESONA  II', 'LA TERESONA   III', 'SECTOR POPULAR'],
    "SANTA ANA TLAPALTITLAN": ['16 DE SEPTIEMBRE', 'PINO SUAREZ', 'DEL PANTEON', 'INDEPENDENCIA', 'SANTA MARIA SUR', 'SANTA MARIA NORTE', 'BUENAVISTA'],
    "SANTA CRUZ ATZCAPOTZALTONGO": ['SANTA CRUZ SUR', 'SANTA CRUZ NORTE', 'EX HACIENDA LA MAGDALENA'],
    "SANTA MARIA DE LAS ROSAS": ['SANTA MARIA DE LAS ROSAS', 'NUEVA SANTA MARIA DE LAS ROSAS', 'UNIDAD VICTORIA', 'LA MAGDALENA', 'NUEVA SANTA MARIA', 'BENITO JUAREZ', 'EVA SAMANO DE LOPEZ MATEOS', 'EMILIANO ZAPATA'],
    "SANTA MARIA TOTOLTEPEC": ['CENTRO', 'EL COECILLO', 'HEROES', 'PASEO TOTOLTEPEC', 'EL OLIMPO', 'EL CARMEN TOTOLTEPEC'],
    "SANTIAGO MILTEPEC": ['MILTEPEC CENTRO', 'MILTEPEC SUR', 'MILTEPEC NORTE'],
    "SANTIAGO TLACOTEPEC": ['DEL CENTRO', 'SANTA MARIA', 'SHINGADE', 'CRISTO REY', 'EL CALVARIO', 'SANTA JUANITA', 'EL REFUGIO'],
    "SANTIAGO TLAXOMULCO": ['EL CALVARIO', 'LA PEÑA', 'JUNTA LOCAL DE CAMINOS'],
    "SAUCES": ['SAUCES I', 'SAUCES III', 'SAUCES IV', 'SAUCES VI', 'SAUCES V', 'VILLAS SANTIN I', 'VILLAS SANTIN II', 'FRANCISCO VILLA', 'SAUCES II'],
    "SEMINARIO 2 DE MARZO": ['SEMINARIO 4A SECCION I', 'SEMINARIO 4A SECCION II', 'HEROES 5 DE MAYO I', 'HEROES 5 DE MAYO II'],
    "SEMINARIO CONCILIAR": ['SEMINARIO EL PARQUE', 'SEMINARIO 3A SECCION', 'SEMINARIO 1A SECCION', 'SEMINARIO EL MODULO'],
    "SEMINARIO LAS TORRES": ['SEMINARIO SAN FELIPE DE JESUS', 'SEMINARIO 2A SECCION', 'SEMINARIO 5A SECCION'],
    "TECAXIC": ['TECAXIC ORIENTE', 'TECAXIC PONIENTE'],
    "TLACHALOYA": ['TLACHALOYA', 'BALBUENA', 'SAN CARLOS', 'SAN JOSE BUENAVISTA', 'DEL CENTRO', 'EL TEJOCOTE', 'SAN JOSE LA COSTA'],
    "UNIVERSIDAD": ['UNIVERSIDAD', 'CUAUHTEMOC', 'AMERICAS', 'ALTAMIRANO'],
}

MAPA_UTB_DEL = {utb: dl for dl, lista in CATALOGO_MAESTRO.items() for utb in lista}

# --- 1.6 INVENTARIO MAESTRO (SF6) ---
STOCK_INICIAL = [
    {"ID": "LUM-01", "Material": "Luminaria LED 100W", "Stock": 150, "Min": 20, "Unidad": "Piezas"},
    {"ID": "FOT-02", "Material": "Fotocelda Universal", "Stock": 300, "Min": 50, "Unidad": "Piezas"},
    {"ID": "CAB-03", "Material": "Cable Aluminio Neutra 2+1", "Stock": 5000, "Min": 500, "Unidad": "Metros"},
    {"ID": "BRA-04", "Material": "Brazo Galvanizado 1.5m", "Stock": 80, "Min": 15, "Unidad": "Piezas"},
    {"ID": "CIN-05", "Material": "Cinta Aisgla Super 33", "Stock": 200, "Min": 30, "Unidad": "Piezas"},
    {"ID": "PIN-06", "Material": "Pintura Esmalte (Comex)", "Stock": 50, "Min": 10, "Unidad": "Litros"},
    {"ID": "THI-07", "Material": "Tíner Estándar", "Stock": 40, "Min": 8, "Unidad": "Litros"},
    {"ID": "CEM-08", "Material": "Cemento Gris CPC 30", "Stock": 100, "Min": 15, "Unidad": "Bultos"},
    {"ID": "GRA-09", "Material": "Grava Triturada", "Stock": 30, "Min": 5, "Unidad": "Metro Cúbico"},
    {"ID": "ARE-10", "Material": "Arena de Mina", "Stock": 45, "Min": 5, "Unidad": "Metro Cúbico"},
    {"ID": "CON-11", "Material": "Conectores Línea Bimetálicos", "Stock": 500, "Min": 50, "Unidad": "Cajas"},
    {"ID": "REC-12", "Material": "Residuo/Escombro Limpio", "Stock": 1000, "Min": 0, "Unidad": "Kilos"}
]

# --- 2. MOTOR LÓGICO MEJORADO ---
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
    df = pd.read_excel(file, engine='openpyxl') if extension == 'xlsx' else pd.read_csv(file)
    df = df.dropna(how='all').reset_index(drop=True)
    df = df[df.iloc[:, 0].astype(str).str.strip() != "nan"]
    df = df[df.iloc[:, 0].astype(str).str.strip() != ""]
    df = df[df.iloc[:, 0].notna()]
    df['del_norm'] = df.iloc[:, 22].astype(str).apply(normalizar_texto)
    df['utb_norm'] = df.iloc[:, 23].astype(str).apply(normalizar_texto)
    return df

# --- 3. AUTENTICACIÓN Y ESTADO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = False, None, ""
if "menu" not in st.session_state:
    st.session_state.menu = "Inicio"
if "lista_bajas" not in st.session_state:
    st.session_state.lista_bajas = {}
if "input_key" not in st.session_state:
    st.session_state.input_key = 0
if "pasos_sf4" not in st.session_state:
    st.session_state.pasos_sf4 = [] 
if "edit_index" not in st.session_state:
    st.session_state.edit_index = -1

if "boveda_mmd" not in st.session_state:
    if os.path.exists("boveda_pangea.json"):
        with open("boveda_pangea.json", "r", encoding="utf-8") as f:
            st.session_state.boveda_mmd = json.load(f)
    else:
        st.session_state.boveda_mmd = {}

if not st.session_state.autenticado:
    st.title("🔐 Acceso SF PANGEA")
    col_u, col_p = st.columns(2)
    with col_u: u = st.text_input("Usuario")
    with col_p: p = st.text_input("Contraseña", type="password")
    if st.button("🚀 Ingresar", use_container_width=True):
        if u == "SF" and p == "1827":
            st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = True, "ADMIN", "SF_ADMIN"
            st.rerun()
        elif u == "GuaDAP" and p == "1111":
            st.session_state.autenticado, st.session_state.perfil, st.session_state.usuario_nombre = True, "CONSULTA", "GuaDAP"
            st.rerun()
        else:
            st.error("Acceso denegado")
else:
    # --- 4. SIDEBAR ---
    with st.sidebar:
        st.title("⚙️ Panel Operativo")
        st.write(f"**Usuario:** {st.session_state.usuario_nombre}")
        st.write("---")
        if st.button("🏠 Inicio", use_container_width=True): st.session_state.menu = "Inicio"
        if st.button("🚀 SF1-Generador de Rutas", use_container_width=True): st.session_state.menu = "SF1"
        if st.button("📁 SF2-Bajas", use_container_width=True): st.session_state.menu = "SF2"
        if st.button("📊 SF3-Captura y Métricas", use_container_width=True): st.session_state.menu = "SF3"
        if st.button("🏗️ SF4-Diseño de Procesos", use_container_width=True): st.session_state.menu = "SF4"
        if st.button("🛡️ SF5-Anti-Duplicados", use_container_width=True): st.session_state.menu = "SF5"
        if st.button("📦 SF6-Almacén e Inventario", use_container_width=True): st.session_state.menu = "SF6"
        st.write("---")
        if st.session_state.menu == "SF1":
            st.subheader("📊 Ajustes GdR Multi-Ruta")
            t_por_punto = st.slider("Minutos por Atención", 5, 60, 20)
            v_promedio = st.slider("Velocidad km/h", 10, 80, 25)
            max_puntos_ruta = st.slider("Puntos Máximos por Ruta (Segmentación):", 5, 50, 15) # <--- NUEVO CONTROL DE LA V24
            st.write("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
        st.info("SF PANGEA V24")

# --- 5. CUERPO LÓGICO ---
    if st.session_state.menu == "Inicio":
        st.title("👋 Bienvenido a SF PANGEA")
        st.info("Sistema de Gestión Operativa - Dirección de Alumbrado Público")
        st.write("Seleccione un módulo en el menú lateral para comenzar.")
        st.image("https://img.icons8.com/clouds/500/000000/map-marker.png", width=150)

    elif st.session_state.menu == "SF3":
        st.title(f"🛠️ Módulo SF3 - Gestión y Métricas")

        if "reset_key" not in st.session_state:
            st.session_state.reset_key = 0
        rk = st.session_state.reset_key

        with st.expander("📝 REGISTRAR NUEVA ATENCIÓN (FORMULARIO)", expanded=False):
            st.write("📍 **Paso 1: Ubicación**")
            col_geo1, col_geo2 = st.columns(2)
            with col_geo1:
                f_del = st.selectbox("Delegación", sorted(list(CATALOGO_MAESTRO.keys())), key=f"del_manual_{rk}")
            with col_geo2:
                opciones_utb_f = sorted(CATALOGO_MAESTRO.get(f_del, []))
                f_utb = st.selectbox("UTB", opciones_utb_f, key=f"utb_manual_{rk}")

            with st.form(key=f"form_sf3_core_{rk}", clear_on_submit=True):
                st.write("📝 **Paso 2: Detalles de la Atención**")
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1: f_fecha = st.date_input("Fecha")
                with c2: f_ot = st.text_input("O.T.")
                with c3: f_folio = st.text_input("Folio / Ticket / IMEI")
                f_calle = st.text_input("Calle")

                st.markdown("---")
                st.write("📊 **Cantidades de Trabajo Realizado:**")
                m1, m2, m3, m4 = st.columns(4)
                with m1: f_rehab = st.number_input("7. Rehabilitación", min_value=0, step=1)
                with m2: f_manto = st.number_input("8. Mantenimiento", min_value=0, step=1)
                with m3: f_sust = st.number_input("9. Sustitución", min_value=0, step=1)
                with m4: f_ampli = st.number_input("10. Ampliación", min_value=0, step=1)

                f_obs = st.text_area("11. Observaciones")
                btn_guardar = st.form_submit_button("🚀 GUARDAR REGISTRO EN LISTA", use_container_width=True)

                if btn_guardar:
                    if "manual_db" not in st.session_state: st.session_state.manual_db = []
                    st.session_state.manual_db.append({
                        "FECHA": f_fecha.strftime("%d/%m/%Y"), "OT": f_ot.upper(), "CALLE": f_calle.upper(),
                        "DELEGACIÓN": f_del, "UTB": f_utb, "FOLIO": f_folio.upper(),
                        "REHAB": f_rehab, "MANTO": f_manto, "SUST": f_sust, "AMPLI": f_ampli, "OBS": f_obs
                    })
                    st.session_state.reset_key += 1
                    st.toast(f"O.T. {f_ot} registrada correctamente", icon="✅")
                    time.sleep(0.5)
                    st.rerun()

        if "manual_db" in st.session_state and st.session_state.manual_db:
            if st.button("🗑️ Borrar Último Registro Manual", use_container_width=True):
                st.session_state.manual_db.pop()
                st.rerun()

        st.markdown("---")
        up_cap = st.file_uploader("📂 Opcional: Cargar Archivo de Captura Masiva", type=["csv", "xlsx"], key="up_cap_sf3")
        
        if up_cap:
            try:
                ext = 'xlsx' if up_cap.name.endswith('.xlsx') else 'csv'
                df_temp = load_massive_data(up_cap, ext)
                df_temp = df_temp[~df_temp.iloc[:, 0].astype(str).str.contains("IDENTIFICACION|CIUDADANO|JEFE", case=False, na=False)]
                st.session_state.masivo_pangea = df_temp
            except Exception as e:
                st.error(f"Error procesando archivo: {e}")

        if "masivo_pangea" not in st.session_state:
            st.session_state.masivo_pangea = None

        total_rehab, total_manto, total_sust, total_ampli = 0, 0, 0, 0
        col_f1, col_f2 = st.columns(2)
        if 'sel_del_val' not in st.session_state: st.session_state.sel_del_val = "TODAS"
        if 'sel_utb_val' not in st.session_state: st.session_state.sel_utb_val = "TODAS"

        def sincronizar_filtros():
            u_actual = st.session_state.sel_utb_val
            if u_actual != "TODAS":
                delegacion_perteneciente = MAPA_UTB_DEL.get(u_actual)
                if delegacion_perteneciente: st.session_state.sel_del_val = delegacion_perteneciente

        def cambio_delegacion(): st.session_state.sel_utb_val = "TODAS"

        lista_delegaciones = ["TODAS"] + sorted(list(CATALOGO_MAESTRO.keys()))
        sel_del = col_f1.selectbox("📍 Filtrar TODO por Delegación:", lista_delegaciones, key="sel_del_val", on_change=cambio_delegacion)
        
        lista_utbs_mostrar = ["TODAS"] + (sorted(CATALOGO_MAESTRO.get(sel_del, [])) if sel_del != "TODAS" else sorted(list(MAPA_UTB_DEL.keys())))
        sel_utb = col_f2.selectbox("🔍 Filtrar TODO por UTB:", lista_utbs_mostrar, key="sel_utb_val", on_change=sincronizar_filtros)

        pieces_reporte = []

        if "manual_db" in st.session_state and st.session_state.manual_db:
            df_m = pd.DataFrame(st.session_state.manual_db)
            if sel_del != "TODAS": df_m = df_m[df_m['DELEGACIÓN'] == sel_del]
            if sel_utb != "TODAS": df_m = df_m[df_m['UTB'] == sel_utb]
            if not df_m.empty: pieces_reporte.append(df_m)

        if st.session_state.masivo_pangea is not None:
            df_filt = st.session_state.masivo_pangea.copy()
            if sel_del != "TODAS": df_filt = df_filt[df_filt['del_norm'] == normalizar_texto(sel_del)]
            if sel_utb != "TODAS": df_filt = df_filt[df_filt['utb_norm'] == normalizar_texto(sel_utb)]
            
            if not df_filt.empty:
                df_archivo_v = df_filt.iloc[:, [4, 6, 15, 19, 22, 23, 29, 30, 31, 39]].copy()
                df_archivo_v.columns = ["FECHA", "OT", "FOLIO", "CALLE", "DELEGACIÓN", "UTB", "REHAB", "MANTO", "SUST", "AMPLI"]
                df_archivo_v["OBS"] = ""
                pieces_reporte.append(df_archivo_v)

        if pieces_reporte:
            df_final_vista = pd.concat(pieces_reporte, ignore_index=True)
            cols_num = ["REHAB", "MANTO", "SUST", "AMPLI"]
            for c in cols_num:
                df_final_vista[c] = pd.to_numeric(df_final_vista[c], errors='coerce').fillna(0).astype(int)
            
            total_rehab = df_final_vista["REHAB"].sum()
            total_manto = df_final_vista["MANTO"].sum()
            total_sust = df_final_vista["SUST"].sum()
            total_ampli = df_final_vista["AMPLI"].sum()
            df_final_vista = df_final_vista.astype(str).replace(["nan", "None"], "")
        else:
            df_final_vista = pd.DataFrame()

        st.markdown("### 📊 Resumen Consolidado")
        m_r1, m_r2, m_r3, m_r4 = st.columns(4)
        m_r1.metric("🔧 Rehabilitaciones", int(total_rehab))
        m_r2.metric("🧹 Mantenimientos", int(total_manto))
        m_r3.metric("💡 Sustituciones", int(total_sust))
        m_r4.metric("➕ Ampliaciones", int(total_ampli))

        if not df_final_vista.empty:
            st.dataframe(df_final_vista, use_container_width=True, hide_index=True)
            
            def generar_reporte_con_grafica(df_input, nombre_hoja):
                from openpyxl.chart import BarChart, Reference
                df_temp = df_input.copy()
                cols_n = ["REHAB", "MANTO", "SUST", "AMPLI"]
                for c in cols_n:
                    df_temp[c] = pd.to_numeric(df_temp[c], errors='coerce').fillna(0)
                
                fila_tot = {col: "" for col in df_temp.columns}
                fila_tot["FECHA"] = "TOTALES"
                for c in cols_n: fila_tot[c] = df_temp[c].sum()
                df_reporte = pd.concat([df_temp, pd.DataFrame([fila_tot])], ignore_index=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_reporte.to_excel(writer, index=False, sheet_name=nombre_hoja)
                    wb = writer.book
                    ws = wb[nombre_hoja]
                    
                    chart = BarChart()
                    chart.type = "col"
                    chart.style = 10
                    chart.title = f"Resumen de Trabajo - {nombre_hoja}"
                    chart.y_axis.title = 'Cantidad'
                    chart.x_axis.title = 'Actividades'
                    
                    idx_inicio = df_reporte.columns.get_loc("REHAB") + 1
                    idx_fin = df_reporte.columns.get_loc("AMPLI") + 1
                    fila_totales = len(df_reporte) + 1
                    
                    data = Reference(ws, min_col=idx_inicio, max_col=idx_fin, min_row=fila_totales, max_row=fila_totales)
                    cats = Reference(ws, min_col=idx_inicio, max_col=idx_fin, min_row=1, max_row=1)
                    
                    chart.add_data(data, titles_from_data=False)
                    chart.set_categories(cats)
                    ws.add_chart(chart, "M2")
                return output.getvalue()

            st.write("---")
            st.subheader("📥 Descargar Reportes con Gráficas")
            d_col1, d_col2, d_col3 = st.columns(3)

            if st.session_state.masivo_pangea is not None:
                df_m_f = st.session_state.masivo_pangea.copy()
                if sel_del != "TODAS": df_m_f = df_m_f[df_m_f['del_norm'] == normalizar_texto(sel_del)]
                if sel_utb != "TODAS": df_m_f = df_m_f[df_m_f['utb_norm'] == normalizar_texto(sel_utb)]
                if not df_m_f.empty:
                    df_m_out = df_m_f.iloc[:, [4, 6, 15, 19, 22, 23, 29, 30, 31, 39]].copy()
                    df_m_out.columns = ["FECHA", "OT", "FOLIO", "CALLE", "DELEGACIÓN", "UTB", "REHAB", "MANTO", "SUST", "AMPLI"]
                    xlsx_masivo = generar_reporte_con_grafica(df_m_out, "MASIVO")
                    d_col1.download_button("📂 Reporte MASIVO", xlsx_masivo, "REPORTE_MASIVO.xlsx", use_container_width=True)

            if "manual_db" in st.session_state and st.session_state.manual_db:
                df_man_f = pd.DataFrame(st.session_state.manual_db)
                if sel_del != "TODAS": df_man_f = df_man_f[df_man_f['DELEGACIÓN'] == sel_del]
                if sel_utb != "TODAS": df_man_f = df_man_f[df_man_f['UTB'] == sel_utb]
                if not df_man_f.empty:
                    xlsx_manual = generar_reporte_con_grafica(df_man_f, "MANUAL")
                    d_col2.download_button("📝 Reporte MANUAL", xlsx_manual, "REPORTE_MANUAL.xlsx", use_container_width=True)

            xlsx_unificado = generar_reporte_con_grafica(df_final_vista, "UNIFICADO")
            d_col3.download_button("🚀 Reporte UNIFICADO", xlsx_unificado, "REPORTE_UNIFICADO.xlsx", use_container_width=True)

    elif st.session_state.menu == "SF2":
        st.title("📁 SF2 - Módulo de Baja de Folios")
        st.write("Cargue el archivo original y digite los folios para generar el documento de cierre.")
        
        up_sf2 = st.file_uploader("Subir Archivo de Referencia (Excel/CSV)", type=["csv", "xlsx"], key="sf2_up")
        
        if up_sf2:
            try:
                df_ref = pd.read_excel(up_sf2, dtype=str).fillna("") if up_sf2.name.endswith('.xlsx') else pd.read_csv(up_sf2, encoding='latin-1', dtype=str).fillna("")
                id_col_sf2 = next((c for c in df_ref.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID','IMEI'])), df_ref.columns[0])
                c_input, c_lista = st.columns([1, 1])
                
                with c_input:
                    st.subheader("⌨️ Captura de Folios")
                    with st.form(key=f"form_bajas_{st.session_state.input_key}", clear_on_submit=True):
                        col_f_in, col_ot_in = st.columns([1.2, 1.0])
                        with col_f_in:
                            in_f_val = st.text_input("Digite Folio/Ticket/IMEi:", key=f"f_{st.session_state.input_key}")
                        with col_ot_in:
                            in_ot_val = st.text_input("Orden de Trabajo (O.T.):", key=f"ot_{st.session_state.input_key}")
                        
                        col_cal_in, col_man_in = st.columns([1.1, 1.1])
                        with col_cal_in:
                            date_picker = st.date_input("Fecha (Calendario):", value=pd.Timestamp.now().date(), key=f"dt_p_{st.session_state.input_key}")
                        with col_man_in:
                            date_manual = st.text_input("Fecha (Copiar/Pegar):", placeholder="DD/MM/AAAA", key=f"dt_m_{st.session_state.input_key}")
                        
                        st.markdown("---")
                        in_libre_val = st.text_input("Respuesta Libre / Observaciones (Máx 30 car.):", max_chars=30, key=f"lb_{st.session_state.input_key}")
                        submitted = st.form_submit_button("➕ Agregar a Lista", use_container_width=True)
                        
                        if submitted:
                            f_final = in_f_val.strip()
                            if f_final:
                                if f_final in df_ref[id_col_sf2].astype(str).values:
                                    if date_manual.strip():
                                        fecha_final_texto = date_manual.strip()
                                    else:
                                        fecha_final_texto = date_picker.strftime("%d/%m/%Y")
                                    
                                    ot_part = f"O.T. {in_ot_val.strip()}" if in_ot_val.strip() else ""
                                    libre_part = in_libre_val.strip()
                                    
                                    if not libre_part:
                                        componentes = [c for c in [ot_part, "ATENDIDO", fecha_final_texto] if c]
                                        c_final = " | ".join(componentes)
                                    else:
                                        componentes = [c for c in [ot_part, fecha_final_texto, libre_part] if c]
                                        c_final = " | ".join(componentes)
                                    
                                    st.session_state.lista_bajas[f_final] = c_final
                                    st.toast(f"Folio {f_final} validado", icon="✅")
                                    st.session_state.input_key += 1
                                    st.rerun()
                                else:
                                    st.error(f"⚠️ El folio '{f_final}' no existe en el archivo cargado. Verifique.")
                            else:
                                st.warning("⚠️ Por favor digite un folio antes de agregar.")

                with c_lista:
                    PATH_BAJAS_DB = "boveda_bajas.json"
                    if "db_bajas_historico" not in st.session_state:
                        if os.path.exists(PATH_BAJAS_DB):
                            with open(PATH_BAJAS_DB, "r", encoding="utf-8") as f:
                                st.session_state.db_bajas_historico = json.load(f)
                        else:
                            st.session_state.db_bajas_historico = {}

                    tab_actual, tab_boveda = st.tabs(["📋 Captura Actual", "📂 Bóveda de Historial"])

                    with tab_actual:
                        st.subheader("Folios en proceso de baja")
                        if st.session_state.lista_bajas:
                            df_resumen_bajas = pd.DataFrame([{"Folio": rk, "Respuesta 127": v} for rk, v in st.session_state.lista_bajas.items()])
                            st.dataframe(df_resumen_bajas, use_container_width=True, hide_index=True)
                            
                            if st.button("📥 Generar Documento de Bajas", use_container_width=True, type="primary"):
                                st.balloons()
                                folios_a_buscar = list(st.session_state.lista_bajas.keys())
                                df_final_bajas = df_ref[df_ref[id_col_sf2].astype(str).isin(folios_a_buscar)].copy()
                                
                                mapa_limpio = {str(key).strip(): str(val) for key, val in st.session_state.lista_bajas.items()}
                                df_final_bajas['RESPUESTA 127'] = df_final_bajas[id_col_sf2].astype(str).str.strip().map(mapa_limpio)
                                
                                output_sf2 = io.BytesIO()
                                with pd.ExcelWriter(output_sf2, engine='openpyxl') as writer:
                                    df_final_bajas.to_excel(writer, index=False, sheet_name='BAJAS_SF')
                                excel_data = output_sf2.getvalue()

                                id_registro_baja = f"BAJA-{pd.Timestamp.now().strftime('%Y%m%d-%H%M%S')}"
                                st.session_state.db_bajas_historico[id_registro_baja] = {
                                    "fecha_generacion": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S"),
                                    "archivo_origen": up_sf2.name,
                                    "usuario": st.session_state.usuario_nombre,
                                    "total_folios": len(folios_a_buscar),
                                    "datos_capture": dict(st.session_state.lista_bajas),
                                    "excel_base64": base64.b64encode(excel_data).decode('utf-8')
                                }
                                with open(PATH_BAJAS_DB, "w", encoding="utf-8") as f:
                                    json.dump(st.session_state.db_bajas_historico, f, indent=4, ensure_ascii=False)

                                st.success(f"✅ ¡Documento guardado en Bóveda! ID: {id_registro_baja}")
                                st.download_button(
                                    label="📗 Descargar Excel de Bajas Oficial",
                                    data=excel_data,
                                    file_name=f"BAJAS_{up_sf2.name}",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                            
                            st.write("---")
                            st.write("⚠️ **Zona de Peligro**")
                            seguro_limpieza = st.checkbox("🔐 Confirmar vaciado de la lista actual", key="seguro_limpiar_bajas")
                            if st.button("🗑️ Limpiar Lista Actual", use_container_width=True, type="secondary", disabled=not seguro_limpieza):
                                st.session_state.lista_bajas = {}
                                st.toast("Lista de captura vaciada", icon="🗑️")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            st.info("Esperando captura de folios en la sección izquierda...")

                    with tab_boveda:
                        st.subheader("🗄️ Historial Permanente de Bajas")
                        if st.session_state.db_bajas_historico:
                            lista_tabla_boveda = []
                            for k, v in st.session_state.db_bajas_historico.items():
                                lista_tabla_boveda.append({
                                    "ID Registro": k,
                                    "Fecha": v["fecha_generacion"],
                                    "Origen": v["archivo_origen"],
                                    "Folios": v["total_folios"]
                                })
                            df_boveda_vista = pd.DataFrame(lista_tabla_boveda)
                            st.dataframe(df_boveda_vista.sort_values(by="ID Registro", ascending=False), use_container_width=True, hide_index=True)
                            
                            st.markdown("---")
                            col_recup, col_eliminar = st.columns([2.5, 1.5])
                            
                            with col_recup:
                                st.write("🔍 **Recuperar Documento:**")
                                id_recuperar = st.selectbox("Seleccione ID:", list(st.session_state.db_bajas_historico.keys())[::-1], key="sb_recub_bajas")
                                
                                if id_recuperar:
                                    data_hist = st.session_state.db_bajas_historico[id_recuperar]
                                    with st.expander(f"👁️ Ver folios de {id_recuperar}"):
                                        df_detalles_hist = pd.DataFrame([{"Folio": rk, "Respuesta 127": v} for rk, v in data_hist["datos_capture"].items()])
                                        st.dataframe(df_detalles_hist, use_container_width=True, hide_index=True)
                                    
                                    excel_recuperado_bytes = base64.b64decode(data_hist["excel_base64"])
                                    st.download_button(
                                        label=f"🔄 Volver a descargar Excel",
                                        data=excel_recuperado_bytes,
                                        file_name=f"RECONSTRUIDO_{data_hist['archivo_origen']}",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True
                                    )
                            
                            with col_eliminar:
                                st.write("🚨 **Zona Crítica:**")
                                seguro_borrado_boveda = st.checkbox("🔐 Confirmar borrado físico", key="check_seguro_boveda_bajas")
                                if st.button("🗑️ BORRAR DE BÓVEDA", use_container_width=True, type="secondary", disabled=not seguro_borrado_boveda):
                                    if id_recuperar:
                                        del st.session_state.db_bajas_historico[id_recuperar]
                                        with open(PATH_BAJAS_DB, "w", encoding="utf-8") as f:
                                            json.dump(st.session_state.db_bajas_historico, f, indent=4, ensure_ascii=False)
                                        st.warning(f"ID {id_recuperar} eliminado permanentemente.")
                                        time.sleep(1)
                                        st.rerun()
                        else:
                            st.info("La bóveda está vacía.")
            
            except Exception as e:
                st.error(f"Error en SF2: {e}")
    
    elif st.session_state.menu == "SF1":
        st.title("🚀 GdR V24 - Generador de Rutas Inteligente")
        tab1, tab1_multi, tab2, tab3 = st.tabs([
            "📍 Generador de Ruta Clásico (V23 Pro)", 
            "🚚 Nuevo Motor Multi-Ruta (Pro)", 
            "📂 Bitácora", 
            "🗑️ Papelera"
        ])

        # ==========================================
        # PESTAÑA 1: GENERADOR DE RUTA CLÁSICO (V23 PRO)
        # ==========================================
        with tab1:
            if st.session_state.perfil == "CONSULTA":
                st.warning("⚠️ Modo Consulta activo.")
            else:
                datos_vienen_de_sf5 = "df_transferido" in st.session_state and st.session_state.df_transferido is not None
                if datos_vienen_de_sf5:
                    st.info(f"📦 Usando datos procesados de: {st.session_state.nombre_archivo_transferido}")
                    if st.button("❌ Cancelar y subir otro archivo", key="cancel_c"):
                        st.session_state.df_transferido = None
                        st.rerun()
                    up_c = True
                else:
                    up_c = st.file_uploader("Subir Archivo (Excel/CSV) - Modo Clásico", type=["csv", "xlsx"], key="up_clasico")

                if up_c:
                    try:
                        if datos_vienen_de_sf5:
                            df_raw = st.session_state.df_transferido.copy()
                            up_name = st.session_state.nombre_archivo_transferido
                        else:
                            df_raw = pd.read_excel(up_c, dtype=str).fillna("") if up_c.name.endswith('.xlsx') else pd.read_csv(up_c, encoding='latin-1', dtype=str).fillna("")
                            up_name = up_c.name

                        if 'lat_aux' in df_raw.columns and 'lon_aux' in df_raw.columns and df_raw['lat_aux'].notna().any():
                            df_raw['lat_aux'] = pd.to_numeric(df_raw['lat_aux'], errors='coerce')
                            df_raw['lon_aux'] = pd.to_numeric(df_raw['lon_aux'], errors='coerce')
                        else:
                            col_coor = next((c for c in df_raw.columns if any(p in str(c).lower() for p in ['coordenadas', 'gps', 'ubicacion', 'coord'])), df_raw.columns[0])
                            def limpiar_y_extraer_coordenadas(valor):
                                texto = str(valor).lower().replace("latitude:", "").replace("longitude:", "")
                                numeros = re.findall(r'(-?\d+\.\d+)', texto)
                                if len(numeros) >= 2: return float(numeros[0]), float(numeros[1])
                                return None, None
                            res_coor = df_raw[col_coor].apply(limpiar_y_extraer_coordenadas)
                            df_raw['lat_aux'] = [r[0] for r in res_coor]
                            df_raw['lon_aux'] = [r[1] for r in res_coor]

                        id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                        df_v = df_raw.dropna(subset=['lat_aux', 'lon_aux']).reset_index(drop=True)

                        if not df_v.empty:
                            pts = df_v.to_dict('records')
                            coords_base = np.array([BASE_COORDS])
                            coords_puntos = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                            distancias_a_base = cdist(coords_base, coords_puntos)[0]
                            
                            idx_mas_lejano = np.argmax(distancias_a_base)
                            punto_inicial = pts.pop(idx_mas_lejano)
                            ruta_ordenada = [punto_inicial]
                            last_coord = (punto_inicial['lat_aux'], punto_inicial['lon_aux'])

                            while pts:
                                rest_coords = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                                dist_al_ultimo = cdist([last_coord], rest_coords)[0]
                                dist_a_base = cdist(coords_base, rest_coords)[0]
                                puntuacion_ruta = dist_al_ultimo + (dist_a_base * 0.2)
                                
                                idx_proximo = np.argmin(puntuacion_ruta)
                                proximo_punto = pts.pop(idx_proximo)
                                ruta_ordenada.append(proximo_punto)
                                last_coord = (proximo_punto['lat_aux'], proximo_punto['lon_aux'])

                            route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ruta_ordenada] + [BASE_COORDS]
                            geo_trazo, dist_real_km = get_real_route(route_coords)
                            if not dist_real_km: 
                                dist_real_km = (len(ruta_ordenada) + 1) * 1.3
                                st.warning("🛰️ Servidor de rutas fuera de línea. El KML usará trazo directo.")

                            tot_lums, tot_postes, tot_cable = 0, 0, 0
                            cols_orig = [c for c in df_raw.columns if c not in ['lat_aux', 'lon_aux']]
                            
                            for idx_r, p in enumerate(ruta_ordenada, 1):
                                p['Ruta_Asignada'] = "Ruta_Unica"
                                p['No_Ruta'] = idx_r
                                p['ID_Pangea_Nombre'] = p[id_col]
                                p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 and extraer_carga_robusta(p, 'cable')==0 else 0)
                                p['Cant_Postes'] = extraer_carga_robusta(p, 'poste')
                                p['Cant_Cable_m'] = extraer_carga_robusta(p, 'cable')
                                p['Maps'] = f"https://www.google.com/maps?q={p['lat_aux']},{p['lon_aux']}"
                                
                                tot_lums += p['Cant_Luminarias']
                                tot_postes += p['Cant_Postes']
                                tot_cable += p['Cant_Cable_m']

                            min_totales = ((tot_lums + tot_postes) * t_por_punto) + (dist_real_km / v_promedio * 60)
                            t_estimado = f"{int(min_totales // 60)} h {int(min_totales % 60)} m"

                            st.subheader("📊 Resumen de Ruta Única (Clásica)")
                            mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
                            mc1.metric("📍 Puntos", len(ruta_ordenada))
                            mc2.metric("💡 Luminarias", tot_lums)
                            mc3.metric("🏗️ Postes", tot_postes)
                            mc4.metric("🧶 Cable", f"{tot_cable} m")
                            mc5.metric("🛣️ Distancia", f"{round(dist_real_km, 2)} km")
                            mc6.metric("⏱️ Tiempo Est.", t_estimado)

                            df_export_c = pd.DataFrame(ruta_ordenada)
                            cols_vits = ['Ruta_Asignada', 'No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']
                            columnas_finales = cols_vits + [c for c in df_raw.columns if c != id_col and c not in ['lat_aux', 'lon_aux', 'ï»¿No_Ruta', 'Maps', 'Ruta_Asignada']]
                            df_export_c = df_export_c[columnas_finales]

                            st.dataframe(df_export_c, use_container_width=True, hide_index=True)

                            st.write("---")
                            cc1, cc2, cc3, cc4 = st.columns(4)
                            
                            buf_xlsx_c = io.BytesIO()
                            with pd.ExcelWriter(buf_xlsx_c, engine='openpyxl') as writer:
                                df_export_c.to_excel(writer, index=False, sheet_name='Ruta_Clasica_SF')
                                ws = writer.sheets['Ruta_Clasica_SF']
                                last_row = len(ruta_ordenada) + 1
                                res_row = last_row + 2
                                
                                ws.cell(row=res_row, column=2, value="--- RESUMEN OPERATIVO DINÁMICO ---")
                                ws.cell(row=res_row+1, column=1, value="Total Puntos:"); ws.cell(row=res_row+1, column=2, value=len(ruta_ordenada))
                                ws.cell(row=res_row+2, column=1, value="Total Luminarias:"); ws.cell(row=res_row+2, column=2, value=f"=SUM(D2:D{last_row})")
                                ws.cell(row=res_row+3, column=1, value="Total Postes:"); ws.cell(row=res_row+3, column=2, value=f"=SUM(E2:E{last_row})")
                                ws.cell(row=res_row+4, column=1, value="Total Cable:"); ws.cell(row=res_row+4, column=2, value=f"=SUM(F2:F{last_row})")
                                ws.cell(row=res_row+5, column=1, value="Distancia:"); ws.cell(row=res_row+5, column=2, value=f"{round(dist_real_km,2)} km")
                                
                                f_calc = f"ROUND(((B{res_row+2}+B{res_row+3})*{t_por_punto})+({round(dist_real_km,2)}/{v_promedio}*60),0)"
                                ws.cell(row=res_row+6, column=1, value="Tiempo Estimado:")
                                ws.cell(row=res_row+6, column=2, value=f'=INT({f_calc}/60) & " h " & MOD({f_calc},60) & " m"')
                                
                                fg, fa = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid"), PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
                                for r in range(2, last_row + 1):
                                    if int(df_export_c.iloc[r-2]['Cant_Postes']) > 0:
                                        for cell in ws[r]: cell.fill = fg
                                    elif int(df_export_c.iloc[r-2]['Cant_Cable_m']) > 0:
                                        for cell in ws[r]: cell.fill = fa

                            cc1.download_button("📗 Excel Pro Dinámico", buf_xlsx_c.getvalue(), file_name=f"SF_CLASICA_{up_name}.xlsx", use_container_width=True)
                            
                            csv_buffer = io.StringIO()
                            df_export_c.to_csv(csv_buffer, index=False)
                            csv_buffer.write(f"\n--- RESUMEN OPERATIVO DINÁMICO ---\n")
                            csv_buffer.write(f"Total Puntos:,{len(ruta_ordenada)}\n")
                            csv_buffer.write(f"Total Luminarias:,{tot_lums}\n")
                            csv_buffer.write(f"Total Postes:,{tot_postes}\n")
                            csv_buffer.write(f"Total Cable:,{tot_cable} m\n")
                            csv_buffer.write(f"Distancia Total:,{round(dist_real_km,2)} km\n")
                            csv_buffer.write(f"Tiempo Estimado:,{t_estimado}\n")
                            cc2.download_button("📊 CSV Estático", csv_buffer.getvalue().encode('utf-8-sig'), file_name=f"SF_CLASICA_{up_name}.csv", use_container_width=True)

                            kml_c = simplekml.Kml()
                            folder_c = kml_c.newfolder(name=f"🚚 Ruta Única Clásica ({len(ruta_ordenada)} Pts)")
                            
                            for p in ruta_ordenada:
                                pnt = folder_c.newpoint(name=f"[Ruta_Unica-#{p['No_Ruta']}] {p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
                                h = "<![CDATA[<table border='1' style='width:300px; border-collapse:collapse; font-family:Arial; font-size:12px;'>"
                                h += "<tr><td bgcolor='#767171' colspan='2' align='center'><b style='color:white;'>DATOS DEL REPORTE</b></td></tr>"
                                for col in cols_orig:
                                    val = str(p.get(col, '')).strip()
                                    if val: h += f"<tr><td bgcolor='#F2F2F2'><b>{col}:</b></td><td>{val}</td></tr>"
                                h += "<tr><td bgcolor='#1F4E78' colspan='2' align='center'><b style='color:white;'>DESGLOSE OPERATIVO</b></td></tr>"
                                h += f"<tr><td bgcolor='#D9EAD3'><b>Punto de Ruta:</b></td><td>{p['No_Ruta']}</td></tr>"
                                h += f"<tr><td bgcolor='#D9EAD3'><b>Luminarias:</b></td><td>{p['Cant_Luminarias']}</td></tr>"
                                h += f"<tr><td bgcolor='#D9EAD3'><b>Postes:</b></td><td>{p['Cant_Postes']}</td></tr>"
                                h += f"<tr><td bgcolor='#D9EAD3'><b>Cable:</b></td><td>{p['Cant_Cable_m']} m</td></tr>"
                                h += f"<tr><td bgcolor='#C00000' colspan='2' align='center'><b style='color:white;'>--- RESUMEN OPERATIVO DINÁMICO ---</b></td></tr>"
                                h += f"<tr><td><b>Total Puntos:</b></td><td>{len(ruta_ordenada)}</td></tr>"
                                h += f"<tr><td><b>Total Luminarias Ruta:</b></td><td>{tot_lums}</td></tr>"
                                h += f"<tr><td><b>Total Postes Ruta:</b></td><td>{tot_postes}</td></tr>"
                                h += f"<tr><td><b>Total Cable Ruta:</b></td><td>{tot_cable} m</td></tr>"
                                h += f"<tr><td><b>Distancia Total:</b></td><td>{round(dist_real_km,2)} km</td></tr>"
                                h += f"<tr><td><b>Tiempo Est.:</b></td><td>{t_estimado}</td></tr>"
                                h += "</table>]]>"
                                pnt.description = h

                            if geo_trazo:
                                ls = folder_c.newlinestring(name="TRAYECTO VIAL COMPLETO (BASE-RUTA-BASE)")
                                ls.coords = [(float(c[0]), float(c[1])) for c in geo_trazo]
                                ls.style.linestyle.width = 6
                                ls.style.linestyle.color = 'ff0000ff'
                            else:
                                ls = folder_c.newlinestring(name="TRAYECTO DIRECTO (SIN CALLES)")
                                ls.coords = [(float(c[1]), float(c[0])) for c in route_coords]
                                ls.style.linestyle.width = 4
                                ls.style.linestyle.color = 'ff00ffff'

                            cc3.download_button("🗺️ KML Maestro Clásico", kml_c.kml(), file_name=f"SF_CLASICA_{up_name}.kml", use_container_width=True)
                            cc4.link_button("🚀 My Maps", "https://www.google.com/maps/d/", use_container_width=True)

                            if st.button("💾 REGISTRAR RUTA CLÁSICA EN BITÁCORA", use_container_width=True, key="reg_c"):
                                try:
                                    conn = st.connection("gsheets", type=GSheetsConnection)
                                    hist = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                                    info_j = f"Modo: Clásico, Pts: {len(ruta_ordenada)}, Lums: {tot_lums}, Cab: {tot_cable}m, Dist: {round(dist_real_km,1)}km"
                                    n_f = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Nombre_Ruta": f"CLASICA_{up_name}", "Usuario_Generador": st.session_state.usuario_nombre, "Datos_JSON": info_j}])
                                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([hist, n_f], ignore_index=True))
                                    st.balloons(); st.success("¡Bitácora actualizada!")
                                except Exception as e: st.error(f"Error GSheets: {e}")
                        else:
                            st.error("No se pudieron extraer coordenadas válidas en Modo Clásico.")
                    except Exception as e: st.error(f"Error en Motor Clásico: {e}")

        # ==========================================
        # PESTAÑA 2: NUEVO MOTOR MULTI-RUTA (PRO)
        # ==========================================
        with tab1_multi:
            if st.session_state.perfil == "CONSULTA":
                st.warning("⚠️ Modo Consulta activo.")
            else:
                max_puntos_ruta = 30  
                datos_vienen_de_sf5 = "df_transferido" in st.session_state and st.session_state.df_transferido is not None
                if datos_vienen_de_sf5:
                    st.info(f"📦 Usando datos procesados de: {st.session_state.nombre_archivo_transferido}")
                    if st.button("❌ Cancelar y subir otro archivo", key="cancel_m"):
                        st.session_state.df_transferido = None
                        st.rerun()
                    up_m = True
                else:
                    up_m = st.file_uploader("Subir Archivo (Excel/CSV) - Modo Multi-Ruta", type=["csv", "xlsx"], key="up_multiruta")

                if up_m:
                    try:
                        if datos_vienen_de_sf5:
                            df_raw = st.session_state.df_transferido.copy()
                            up_name = st.session_state.nombre_archivo_transferido
                        else:
                            df_raw = pd.read_excel(up_m, dtype=str).fillna("") if up_m.name.endswith('.xlsx') else pd.read_csv(up_m, encoding='latin-1', dtype=str).fillna("")
                            up_name = up_m.name

                        if 'lat_aux' in df_raw.columns and 'lon_aux' in df_raw.columns and df_raw['lat_aux'].notna().any():
                            df_raw['lat_aux'] = pd.to_numeric(df_raw['lat_aux'], errors='coerce')
                            df_raw['lon_aux'] = pd.to_numeric(df_raw['lon_aux'], errors='coerce')
                        else:
                            col_coor = next((c for c in df_raw.columns if any(p in str(c).lower() for p in ['coordenadas', 'gps', 'ubicacion', 'coord'])), df_raw.columns[0])
                            def limpiar_y_extraer_coordenadas(valor):
                                texto = str(valor).lower().replace("latitude:", "").replace("longitude:", "")
                                numeros = re.findall(r'(-?\d+\.\d+)', texto)
                                if len(numeros) >= 2: return float(numeros[0]), float(numeros[1])
                                return None, None
                            res_coor = df_raw[col_coor].apply(limpiar_y_extraer_coordenadas)
                            df_raw['lat_aux'] = [r[0] for r in res_coor]
                            df_raw['lon_aux'] = [r[1] for r in res_coor]

                        id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                        df_v = df_raw.dropna(subset=['lat_aux', 'lon_aux']).reset_index(drop=True)

                        if not df_v.empty:
                            pts_restantes = df_v.to_dict('records')
                            lista_rutas_finales = []
                            contador_rutas = 1
                            coords_base = np.array([BASE_COORDS])

                            while len(pts_restantes) > 0:
                                rest_coords = np.array([[p['lat_aux'], p['lon_aux']] for p in pts_restantes])
                                distancias_a_base = cdist(coords_base, rest_coords)[0]
                                idx_mas_lejano = np.argmax(distancias_a_base)
                                
                                punto_inicial = pts_restantes.pop(idx_mas_lejano)
                                ruta_actual_puntos = [punto_inicial]
                                last_coord = (punto_inicial['lat_aux'], punto_inicial['lon_aux'])

                                while len(pts_restantes) > 0 and len(ruta_actual_puntos) < max_puntos_ruta:
                                    rest_coords_loop = np.array([[p['lat_aux'], p['lon_aux']] for p in pts_restantes])
                                    dist_al_ultimo = cdist([last_coord], rest_coords_loop)[0]
                                    dist_a_base_loop = cdist(coords_base, rest_coords_loop)[0]
                                    puntuacion_ruta = dist_al_ultimo + (dist_a_base_loop * 0.2)
                                    
                                    idx_proximo = np.argmin(puntuacion_ruta)
                                    proximo_punto = pts_restantes.pop(idx_proximo)
                                    ruta_actual_puntos.append(proximo_punto)
                                    last_coord = (proximo_punto['lat_aux'], proximo_punto['lon_aux'])

                                lista_rutas_finales.append({
                                    "id_ruta": f"Ruta_{contador_rutas}",
                                    "puntos": ruta_actual_puntos
                                })
                                contador_rutas += 1

                            st.success(f"📦 ¡Segmentación Multi-Ruta Exitosa! Se generaron **{len(lista_rutas_finales)} rutas independientes**.")
                            
                            kml = simplekml.Kml()
                            cols_orig = [c for c in df_raw.columns if c not in ['lat_aux', 'lon_aux']]
                            
                            excel_rutas_desglose = []
                            resumen_global_texto = ""
                            csv_multi_buffer = io.StringIO()
                            
                            tot_puntos_global, tot_lums_global, tot_postes_global, tot_cable_global, tot_dist_global = 0, 0, 0, 0, 0.0
                            metricas_por_ruta = {}

                            for r_info in lista_rutas_finales:
                                r_id = r_info["id_ruta"]
                                r_pts = r_info["puntos"]
                                
                                folder = kml.newfolder(name=f"🚚 {r_id} ({len(r_pts)} Pts)")
                                route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in r_pts] + [BASE_COORDS]
                                
                                geo_trazo, dist_real_km = get_real_route(route_coords)
                                time.sleep(0.3)
                                if not dist_real_km: dist_real_km = (len(r_pts) + 1) * 1.3
                                
                                r_lums, r_postes, r_cable = 0, 0, 0
                                for idx_r, p in enumerate(r_pts, 1):
                                    p['Ruta_Asignada'] = r_id
                                    p['No_Ruta'] = idx_r
                                    p['ID_Pangea_Nombre'] = p[id_col]
                                    p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 and extraer_carga_robusta(p, 'cable')==0 else 0)
                                    p['Cant_Postes'] = extraer_carga_robusta(p, 'poste')
                                    p['Cant_Cable_m'] = extraer_carga_robusta(p, 'cable')
                                    p['Maps'] = f"https://www.google.com/maps?q={p['lat_aux']},{p['lon_aux']}"
                                    
                                    r_lums += p['Cant_Luminarias']
                                    r_postes += p['Cant_Postes']
                                    r_cable += p['Cant_Cable_m']

                                    # --- REPLICACIÓN DE VISTA PREMIUM CDATA EN EL KML MULTI-RUTA ---
                                    pnt = folder.newpoint(name=f"[{r_id}-#{idx_r}] {p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
                                    h = "<![CDATA[<table border='1' style='width:300px; border-collapse:collapse; font-family:Arial; font-size:12px;'>"
                                    h += f"<tr><td bgcolor='#767171' colspan='2' align='center'><b style='color:white;'>DATOS DEL REPORTE ({r_id})</b></td></tr>"
                                    for col in cols_orig:
                                        val = str(p.get(col, '')).strip()
                                        if val: h += f"<tr><td bgcolor='#F2F2F2'><b>{col}:</b></td><td>{val}</td></tr>"
                                    h += "<tr><td bgcolor='#1F4E78' colspan='2' align='center'><b style='color:white;'>DESGLOSE OPERATIVO</b></td></tr>"
                                    h += f"<tr><td bgcolor='#D9EAD3'><b>Punto de Ruta:</b></td><td>{p['No_Ruta']}</td></tr>"
                                    h += f"<tr><td bgcolor='#D9EAD3'><b>Luminarias:</b></td><td>{p['Cant_Luminarias']}</td></tr>"
                                    h += f"<tr><td bgcolor='#D9EAD3'><b>Postes:</b></td><td>{p['Cant_Postes']}</td></tr>"
                                    h += f"<tr><td bgcolor='#D9EAD3'><b>Cable:</b></td><td>{p['Cant_Cable_m']} m</td></tr>"
                                    # ENCABEZADO CORREGIDO: Ahora jala el nombre dinámico del KML idéntico al del Excel Pro
                                    h += f"<tr><td bgcolor='#C00000' colspan='2' align='center'><b style='color:white;'>--- RESUMEN OPERATIVO DINÁMICO ({r_id}) ---</b></td></tr>"
                                    h += f"<tr><td><b>Total Puntos Ruta:</b></td><td>{len(r_pts)}</td></tr>"
                                    h += f"<tr><td><b>Total Luminarias:</b></td><td>{r_lums}</td></tr>"
                                    h += f"<tr><td><b>Total Postes:</b></td><td>{r_postes}</td></tr>"
                                    h += f"<tr><td><b>Total Cable:</b></td><td>{r_cable} m</td></tr>"
                                    h += f"<tr><td><b>Distancia Tramo:</b></td><td>{round(dist_real_km,2)} km</td></tr>"
                                    h += "</table>]]>"
                                    pnt.description = h

                                if geo_trazo:
                                    ls = folder.newlinestring(name=f"Trayecto Vial {r_id}")
                                    ls.coords = [(float(c[0]), float(c[1])) for c in geo_trazo]
                                    ls.style.linestyle.width = 6
                                    ls.style.linestyle.color = 'ff00cc00' 
                                else:
                                    ls = folder.newlinestring(name=f"Trayecto Directo {r_id}")
                                    ls.coords = [(float(c[1]), float(c[0])) for c in route_coords]
                                    ls.style.linestyle.width = 4
                                    ls.style.linestyle.color = 'ff00ffff'
                                
                                min_totales = ((r_lums + r_postes) * t_por_punto) + (dist_real_km / v_promedio * 60)
                                t_estimado_r = f"{int(min_totales // 60)} h {int(min_totales % 60)} m"

                                metricas_por_ruta[r_id] = {
                                    "puntos": len(r_pts), "distancia": round(dist_real_km, 2), "tiempo": t_estimado_r
                                }

                                tot_puntos_global += len(r_pts)
                                tot_lums_global += r_lums
                                tot_postes_global += r_postes
                                tot_cable_global += r_cable
                                tot_dist_global += dist_real_km
                                
                                resumen_global_texto += f"**• {r_id}:** {len(r_pts)} Pts | 💡 {r_lums} Lums | 🏗️ {r_postes} Postes | 🛣️ {round(dist_real_km,1)} km | ⏱️ {t_estimado_r}\n\n"
                                
                                df_temp_r = pd.DataFrame(r_pts)
                                cols_vits = ['Ruta_Asignada', 'No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']
                                columnas_finales = cols_vits + [c for c in df_raw.columns if c != id_col and c not in ['lat_aux', 'lon_aux', 'ï»¿No_Ruta', 'Maps', 'Ruta_Asignada']]
                                df_temp_r = df_temp_r[columnas_finales]
                                excel_rutas_desglose.append(df_temp_r)

                            st.subheader("📊 Resumen Global Consolidado")
                            mg1, mg2, mg3, mg4, mg5 = st.columns(5)
                            mg1.metric("🚚 Total Rutas", len(lista_rutas_finales))
                            mg2.metric("📍 Total Puntos", tot_puntos_global)
                            mg3.metric("💡 Total Luminarias", tot_lums_global)
                            mg4.metric("🏗️ Total Postes", tot_postes_global)
                            mg5.metric("🛣️ Kilometraje Total", f"{round(tot_dist_global, 1)} km")

                            st.markdown("### 📋 Desglose Técnico por Ruta")
                            st.markdown(resumen_global_texto)

                            # --- GENERACIÓN DEL EXCEL PRO MULTI-RESUMEN ---
                            buf_xlsx = io.BytesIO()
                            with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
                                df_maestro_completo = pd.concat(excel_rutas_desglose, ignore_index=True)
                                df_maestro_completo.to_excel(writer, index=False, sheet_name='Plan_De_Rutas_SF')
                                ws = writer.sheets['Plan_De_Rutas_SF']
                                
                                ws.delete_rows(2, ws.max_row)
                                r_actual = 2
                                fg, fa = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid"), PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
                                
                                for df_r in excel_rutas_desglose:
                                    r_id = df_r.iloc[0]['Ruta_Asignada']
                                    m_info = metricas_por_ruta[r_id]
                                    inicio_bloque = r_actual
                                    
                                    for _, fila in df_r.iterrows():
                                        for c_idx, valor in enumerate(fila, 1):
                                            ws.cell(row=r_actual, column=c_idx, value=valor)
                                        
                                        if int(fila['Cant_Postes']) > 0:
                                            for cell in ws[r_actual]: cell.fill = fg
                                        elif int(fila['Cant_Cable_m']) > 0:
                                            for cell in ws[r_actual]: cell.fill = fa
                                        r_actual += 1
                                    
                                    fin_bloque = r_actual - 1
                                    
                                    r_actual += 1
                                    ws.cell(row=r_actual, column=2, value=f"--- RESUMEN OPERATIVO DINÁMICO ({r_id}) ---")
                                    ws.cell(row=r_actual+1, column=1, value="Total Puntos:"); ws.cell(row=r_actual+1, column=2, value=m_info["puntos"])
                                    ws.cell(row=r_actual+2, column=1, value="Total Luminarias:"); ws.cell(row=r_actual+2, column=2, value=f"=SUM(D{inicio_bloque}:D{fin_bloque})")
                                    ws.cell(row=r_actual+3, column=1, value="Total Postes:"); ws.cell(row=r_actual+3, column=2, value=f"=SUM(E{inicio_bloque}:E{fin_bloque})")
                                    ws.cell(row=r_actual+4, column=1, value="Total Cable:"); ws.cell(row=r_actual+4, column=2, value=f"=SUM(F{inicio_bloque}:F{fin_bloque})")
                                    ws.cell(row=r_actual+5, column=1, value="Distancia Tramo:"); ws.cell(row=r_actual+5, column=2, value=f"{m_info['distancia']} km")
                                    ws.cell(row=r_actual+6, column=1, value="Tiempo Estimado:"); ws.cell(row=r_actual+6, column=2, value=m_info["tiempo"])
                                    
                                    r_actual += 9 

                            st.dataframe(df_maestro_completo, use_container_width=True, hide_index=True)

                            # --- GENERACIÓN DEL CSV MULTI-RUTA ESTÁTICO ---
                            for df_r in excel_rutas_desglose:
                                df_r.to_csv(csv_multi_buffer, index=False)
                                r_id = df_r.iloc[0]['Ruta_Asignada']
                                m_info = metricas_por_ruta[r_id]
                                csv_multi_buffer.write(f"\n--- RESUMEN OPERATIVO DINÁMICO ({r_id}) ---\n")
                                csv_multi_buffer.write(f"Total Puntos:,{m_info['puntos']}\n")
                                csv_multi_buffer.write(f"Distancia Total:,{m_info['distancia']} km\n")
                                csv_multi_buffer.write(f"Tiempo Estimado:,{m_info['tiempo']}\n\n")

                            st.write("---")
                            c1, c2, c3, c4 = st.columns(4)
                            c1.download_button("📗 Excel Multi-Resumen Pro", buf_xlsx.getvalue(), file_name=f"SF_MULTI_PRO_{up_name}.xlsx", use_container_width=True)
                            c2.download_button("📊 CSV Multi-Estático", csv_multi_buffer.getvalue().encode('utf-8-sig'), file_name=f"SF_MULTI_PRO_{up_name}.csv", use_container_width=True)
                            c3.download_button("🗺️ KML Maestro Detallado", kml.kml(), file_name=f"SF_MULTI_PRO_{up_name}.kml", use_container_width=True)
                            c4.link_button("🚀 My Maps", "https://www.google.com/maps/d/", use_container_width=True)

                            if st.button("💾 REGISTRAR LOTE EN BITÁCORA", use_container_width=True, key="reg_m"):
                                try:
                                    conn = st.connection("gsheets", type=GSheetsConnection)
                                    hist = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                                    info_j = f"Modo: Multi-Ruta Pro, Rutas: {len(lista_rutas_finales)}, Pts: {tot_puntos_global}, Lums: {tot_lums_global}, Dist: {round(tot_dist_global,1)}km"
                                    n_f = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Nombre_Ruta": f"MULTIRUTA_PRO_{up_name}", "Usuario_Generador": st.session_state.usuario_nombre, "Datos_JSON": info_j}])
                                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([hist, n_f], ignore_index=True))
                                    st.balloons(); st.success("¡Bitácora actualizada!")
                                except Exception as e: st.error(f"Error GSheets: {e}")
                        else:
                            st.error("No se pudieron extraer coordenadas válidas en Modo Multi-Ruta.")
                    except Exception as e: st.error(f"Error en Motor Multi-Ruta V24: {e}")

        # ==========================================
        # PESTAÑA 3: BITÁCORA DE PROCESOS
        # ==========================================
        with tab2:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_bt = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                if not df_bt.empty:
                    df_bt_v = df_bt.copy()
                    df_bt_v.insert(0, "ID_Reg", range(1, len(df_bt_v) + 1))
                    if st.session_state.perfil == "ADMIN":
                        c_sel, c_del = st.columns([3, 1])
                        ids_e = st.multiselect("ID para mover a papelera:", df_bt_v["ID_Reg"].tolist())
                        if c_del.button("🗑️ Mover"):
                            if ids_e:
                                idx_e = df_bt_v[df_bt_v["ID_Reg"].isin(ids_e)].index
                                df_tr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, ttl=0).dropna(how='all')
                                conn.update(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, data=pd.concat([df_tr, df_bt.loc[idx_e]], ignore_index=True))
                                conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=df_bt.drop(idx_e))
                                st.success("Movido."); time.sleep(1); st.rerun()
                    st.dataframe(df_bt_v.sort_values("ID_Reg", ascending=False), hide_index=True, use_container_width=True)
                else: 
                    st.info("Bitácora vacía.")
            except Exception as e: 
                st.info(f"Sincronizando bitácora... {e}")

        # ==========================================
        # PESTAÑA 4: PAPELERA
        # ==========================================
        with tab3:
            if st.session_state.perfil == "ADMIN":
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_tr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, ttl=0).dropna(how='all')
                    if not df_tr.empty:
                        df_tr_v = df_tr.copy()
                        df_tr_v.insert(0, "ID_Reg", range(1, len(df_tr_v) + 1))
                        col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
                        with col_r1: ids_r = st.multiselect("ID para restaurar:", df_tr_v["ID_Reg"].tolist())
                        with col_r2: 
                            if st.button("♻️ Restaurar"):
                                if ids_r:
                                    idx_r = df_tr_v[df_tr_v["ID_Reg"].isin(ids_r)].index
                                    df_pr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([df_pr, df_tr.loc[idx_r]], ignore_index=True))
                                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, data=df_tr.drop(idx_r))
                                    st.success("Restaurado."); time.sleep(1); st.rerun()
                        with col_r3:
                            if st.button("🔥 VACIAR PAPELERA"):
                                df_vacio = pd.DataFrame(columns=df_tr.columns)
                                conn.update(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, data=df_vacio)
                                st.success("¡Papelera purgada!"); time.sleep(1); st.rerun()
                        st.dataframe(df_tr_v, hide_index=True, use_container_width=True)
                    else: 
                        st.info("Papelera vacía.")
                except Exception as e: 
                    st.info(f"Cargando papelera... {e}")
            else:
                st.warning("🔒 Área restringida para administradores.")

    elif st.session_state.menu == "SF4":
        st.title("🏗️ SF4 - Arquitecto de Procesos & Oficios")
        tab_c, tab_b, tab_i, tab_o = st.tabs(["🆕 Constructor Inteligente", "🗄️ Bóveda de Proyectos", "📥 Importación Externa", "📄 GENERADOR DE OFICIOS"])

        with tab_c:
            with st.expander("📝 CONFIGURAR PASO", expanded=True):
                idx = st.session_state.edit_index
                editando = (idx != -1)
                paso_actual = st.session_state.pasos_sf4[idx] if editando else {}
                
                txt = st.text_input("Actividad o Pregunta (usa '?' para bifurcar):", value=paso_actual.get('texto', ""), key=f"txt_sf4_{idx}")
                is_decision = txt.strip().endswith('?')
                destinos = ["Siguiente", "Fin"] + [f"Paso {i+1}" for i in range(len(st.session_state.pasos_sf4))]

                c1, c2, c3 = st.columns(3)
                if not is_decision:
                    with c1: tipo = st.selectbox("Forma:", ["Proceso", "Inicio/Fin"], index=0 if paso_actual.get('tipo') == "Proceso" else (1 if paso_actual.get('tipo') == "Inicio/Fin" else 0))
                    with c2: 
                        d_val = paso_actual.get('conecta_a', "Siguiente")
                        destino = st.selectbox("Conecta a:", destinos, index=destinos.index(d_val) if d_val in destinos else 0)
                    with c3: label = st.text_input("Etiqueta flecha:", value=paso_actual.get('etiqueta_flecha', ""), placeholder="Ej: Ok")
                else:
                    with c1: 
                        label_si = st.text_input("Etiqueta SÍ:", value=paso_actual.get('label_si', "SÍ"))
                        d_si_val = paso_actual.get('dest_si', "Siguiente")
                        dest_si = st.selectbox("Destino SÍ:", destinos, index=destinos.index(d_si_val) if d_si_val in destinos else 0)
                    with c2: 
                        label_no = st.text_input("Etiqueta NO:", value=paso_actual.get('label_no', "NO"))
                        d_no_val = paso_actual.get('dest_no', "Siguiente")
                        dest_no = st.selectbox("Destino NO (Salto):", destinos, index=destinos.index(d_no_val) if d_no_val in destinos else 0)
                    with c3: st.info("Las decisiones requieren dos salidas obligatorias.")

                if not editando:
                    if st.button("➕ Agregar al Flujo", use_container_width=True):
                        if txt:
                            nuevo = {"texto": txt, "is_decision": is_decision}
                            if is_decision: nuevo.update({"label_si": label_si, "dest_si": dest_si, "label_no": label_no, "dest_no": dest_no, "tipo": "Decisión"})
                            else: nuevo.update({"tipo": tipo, "conecta_a": destino, "etiqueta_flecha": label})
                            st.session_state.pasos_sf4.append(nuevo)
                            st.rerun()
                else:
                    cs, cc = st.columns(2)
                    if cs.button("💾 Guardar Cambios", use_container_width=True):
                        nuevo = {"texto": txt, "is_decision": is_decision}
                        if is_decision: nuevo.update({"label_si": label_si, "dest_si": dest_si, "label_no": label_no, "dest_no": dest_no, "tipo": "Decisión"})
                        else: nuevo.update({"tipo": tipo, "conecta_a": destino, "etiqueta_flecha": label})
                        st.session_state.pasos_sf4[idx] = nuevo
                        st.session_state.edit_index = -1
                        st.rerun()
                    if cc.button("❌ Cancelar", use_container_width=True):
                        st.session_state.edit_index = -1
                        st.rerun()

            if st.session_state.pasos_sf4:
                col_l, col_p = st.columns([1, 1.2])
                with col_l:
                    st.subheader("📋 Pasos")
                    for i, p in enumerate(st.session_state.pasos_sf4):
                        with st.container(border=True):
                            cx, cy, cz = st.columns([0.5, 3, 1])
                            cx.write(f"#{i+1}"); cy.write(p['texto'])
                            if cz.button("✏️", key=f"e_{i}"): st.session_state.edit_index = i; st.rerun()
                            if cz.button("🗑️", key=f"d_{i}"): st.session_state.pasos_sf4.pop(i); st.rerun()
                    if st.button("🔥 Reiniciar Mesa", use_container_width=True): st.session_state.pasos_sf4 = []; st.rerun()

                with col_p:
                    st.subheader("📊 Visualización Premium")
                    def clean(t): return re.sub(r'[^a-zA-Z0-9 áéíóúÁÉÍÓÚñÑ]', '', str(t))
                    
                    mmd_head = ["graph TD", "classDef decision fill:#f9f,stroke:#333,stroke-width:2px;", "classDef proceso fill:#bbf,stroke:#333,stroke-width:2px;"]
                    mmd_nodos, mmd_conexiones = [], []

                    for i, p in enumerate(st.session_state.pasos_sf4):
                        id_n = f"N{i}"
                        t_c = clean(p.get('texto', ''))
                        if p.get('tipo') == "Decisión": mmd_nodos.append(f'    {id_n}{{\"{t_c}\"}}:::decision')
                        elif p.get('tipo') == "Inicio/Fin": mmd_nodos.append(f'    {id_n}((\"{t_c}\"))')
                        else: mmd_nodos.append(f'    {id_n}[\"{t_c}\"]:::proceso')

                    for i, p in enumerate(st.session_state.pasos_sf4):
                        id_n = f"N{i}"
                        if not p.get('is_decision', False):
                            tgt = p.get('conecta_a', "Siguiente")
                            lab = p.get('etiqueta_flecha', "")
                            f_style = f'-- "{lab}" -->' if lab else "-->"
                            if tgt == "Siguiente" and i < len(st.session_state.pasos_sf4)-1: mmd_conexiones.append(f'    {id_n} {f_style} N{i+1}')
                            elif tgt == "Fin": mmd_conexiones.append(f'    {id_n} {f_style} Fin([Fin])')
                            elif "Paso" in str(tgt):
                                p_num = int(re.search(r'\d+', str(tgt)).group()) - 1
                                mmd_conexiones.append(f'    {id_n} {f_style} N{p_num}')
                        else:
                            for l_key, d_key in [('label_si', 'dest_si'), ('label_no', 'dest_no')]:
                                dst = p.get(d_key, "Siguiente")
                                lab_f = p.get(l_key, "Opción")
                                f_style = f'-- "{lab_f}" -->'
                                if dst == "Siguiente" and i < len(st.session_state.pasos_sf4)-1: mmd_conexiones.append(f'    {id_n} {f_style} N{i+1}')
                                elif dst == "Fin": mmd_conexiones.append(f'    {id_n} {f_style} Fin([Fin])')
                                elif "Paso" in str(dst):
                                    p_num = int(re.search(r'\d+', str(dst)).group()) - 1
                                    mmd_conexiones.append(f'    {id_n} {f_style} N{p_num}')

                    full_m = "\n".join(mmd_head + mmd_nodos + mmd_conexiones)
                    st.code(full_m, language="mermaid")
                    
                    if st.session_state.pasos_sf4:
                        tema = st.session_state.pasos_sf4[0]['texto'].replace('?', '')
                        st.markdown("---")
                        st.subheader("📝 Objetivos del Proceso")
                        adm, tec = st.columns(2)
                        with adm:
                            st.info("**Administrativo-Normativo**")
                            st.caption(f"Establecer el marco procedimental de '{tema}', asegurando el cumplimiento de los criterios de validación.")
                        with tec:
                            st.success("**Técnico-Operativo**")
                            st.caption(f"Optimizar la respuesta de las cuadrillas en '{tema}', mediante la estandarización técnica.")

                    b64 = base64.b64encode(full_m.encode('utf-8')).decode('utf-8')
                    st.link_button("🚀 LIVE EDITOR", f"https://mermaid.live/edit#base64:{b64}", use_container_width=True)
                    st.write("---")
                    nom_p = st.text_input("Nombre para Bóveda:")
                    if st.button("💾 Guardar en Bóveda Pangea"):
                        if nom_p:
                            st.session_state.boveda_mmd[nom_p] = {"code": full_m, "struct": list(st.session_state.pasos_sf4)}
                            with open("boveda_pangea.json", "w", encoding="utf-8") as f:
                                json.dump(st.session_state.boveda_mmd, f, ensure_ascii=False, indent=4)
                            st.success("Guardado correctamente.")

        with tab_b:
            if not st.session_state.boveda_mmd: st.info("Bóveda vacía.")
            else:
                for k, v in list(st.session_state.boveda_mmd.items()):
                    with st.expander(f"📁 {k}"):
                        st.code(v['code'], language="mermaid")
                        b1, b2, b3 = st.columns(3)
                        if b1.button("🛠️ RECUPERAR", key=f"r_{k}"): st.session_state.pasos_sf4 = list(v['struct']); st.rerun()
                        b_u = base64.b64encode(v['code'].encode('utf-8')).decode('utf-8')
                        b2.link_button("🚀 Live", f"https://mermaid.live/edit#base64:{b_u}")
                        if k.strip().upper() != "PASTEL VERDE":
                            if b3.button("🗑️", key=f"x_{k}", use_container_width=True):
                                del st.session_state.boveda_mmd[k]
                                with open("boveda_pangea.json", "w", encoding="utf-8") as f:
                                    json.dump(st.session_state.boveda_mmd, f, ensure_ascii=False, indent=4)
                                st.rerun()

        with tab_i:
            st.subheader("📥 Importación Externa")
            raw_import = st.text_area("Pega el código Mermaid aquí:", height=300, key="area_import_sf", placeholder="graph TD\nN0((\"Inicio\")) --> N1[\"Proceso\"]")
            
            if st.button("🚀 REDISEÑAR PROCESO", use_container_width=True):
                if raw_import:
                    try:
                        nuevos_pasos = []
                        lineas = [l.strip() for l in raw_import.split('\n') if l.strip()]
                        
                        for linea in lineas:
                            m_io = re.search(r'(\w+)\(\("(.+?)"\)\)', linea)
                            if m_io:
                                nuevos_pasos.append({"texto": m_io.group(2), "tipo": "Inicio/Fin", "is_decision": False, "conecta_a": "Siguiente", "etiqueta_flecha": ""})
                                continue
                            
                            m_dec = re.search(r'(\w+)\{"(.+?)"\}', linea)
                            if m_dec:
                                nuevos_pasos.append({"texto": m_dec.group(2) + "?", "tipo": "Decisión", "is_decision": True, "label_si": "SÍ", "dest_si": "Siguiente", "label_no": "NO", "dest_no": "Fin"})
                                continue

                            m_proc = re.search(r'(\w+)\["(.+?)"\]', linea)
                            if m_proc:
                                nuevos_pasos.append({"texto": m_proc.group(2), "tipo": "Proceso", "is_decision": False, "conecta_a": "Siguiente", "etiqueta_flecha": ""})

                        if nuevos_pasos:
                            st.session_state.pasos_sf4 = nuevos_pasos
                            st.success(f"✅ Se han importado {len(nuevos_pasos)} pasos correctamente.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ No se detectaron nodos válidos en el código. Verifica el formato (N0[\"Texto\"]).")
                    except Exception as e:
                        st.error(f"Error en el motor de importación: {e}")
                else:
                    st.warning("⚠️ El área de texto está vacía.")

        with tab_o:
            st.subheader("📄 Correspondencia Oficial y Control de Bóveda")
            PATH_OFICIOS_DB = "boveda_oficios.json"

            try:
                from fpdf import FPDF
                motor_pdf_listo = True
            except ImportError:
                motor_pdf_listo = False
                st.warning("⚠️ Motor PDF (fpdf) no detectado. Las descargas están deshabilitadas.")

            if "db_oficios" not in st.session_state:
                if os.path.exists(PATH_OFICIOS_DB):
                    with open(PATH_OFICIOS_DB, "r", encoding="utf-8") as f:
                        st.session_state.db_oficios = json.load(f)
                else:
                    st.session_state.db_oficios = {}

            plantillas_maestras = {
                "✅ Atención Exitosa": "Por medio de la presente, se hace de su conocimiento que la petición con folio [FOLIO] ha sido atendida exitosamente por las brigadas de esta Dirección, quedando el servicio en óptimas condiciones de operación.",
                "💡 Ya en Servicio": "Tras la inspección realizada por el personal técnico, se hace de su conocimiento que la luminaria correspondiente al folio [FOLIO] ya se encuentra en servicio y funcionando correctamente.",
                "⏳ Programado/Parcial": "Se informa que la atención al folio [FOLIO] se encuentra en estado parcial; los trabajos continuarán conforme a la disponibilidad de material specialized en el programa de mantenimiento.",
                "🔌 Bajadas de Luz": "Se autoriza la maniobra de bajada de luz solicitada mediante el folio [FOLIO], misma que será coordinada por el personal asignado a la zona correspondiente.",
                "❌ Atención Negativa": "Respecto a la petición [FOLIO], se informa que tras el análisis técnico, la solicitud ha sido determinada como improcedente debido a restricciones normativas o técnicas vigentes.",
                "✏️ Libre (Escribir desde cero)": ""
            }

            c_config, c_preview = st.columns([1, 1.1])

            with c_config:
                modo_of = st.radio("Operación:", ["✨ Crear Nuevo", "📂 Consultar Bóveda"], horizontal=True)
                
                data_previa = {}
                if modo_of == "📂 Consultar Bóveda":
                    if st.session_state.db_oficios:
                        col_sel, col_del = st.columns([3, 1])
                        id_sel = col_sel.selectbox("Seleccionar Oficio:", list(st.session_state.db_oficios.keys())[::-1])
                        data_previa = st.session_state.db_oficios[id_sel]
                        
                        seguro_borrado = st.checkbox("🔐 Confirmar eliminación permanente")
                        if col_del.button("🗑️ BORRAR", use_container_width=True, disabled=not seguro_borrado):
                            del st.session_state.db_oficios[id_sel]
                            with open(PATH_OFICIOS_DB, "w", encoding="utf-8") as f:
                                json.dump(st.session_state.db_oficios, f, indent=4, ensure_ascii=False)
                            st.warning(f"Registro {id_sel} eliminado.")
                            time.sleep(1); st.rerun()
                    else:
                        st.info("La bóveda está vacía.")
                
                with st.container(border=True):
                    st.markdown("**📌 Configuración**")
                    tipo_p = st.selectbox("Plantilla:", list(plantillas_maestras.keys()))
                    c1, c2 = st.columns(2)
                    n_oficio = c1.text_input("No. Oficio:", value=data_previa.get("num", "DAP/___/2026"))
                    f_oficio = c2.date_input("Fecha:", value=pd.to_datetime(data_previa.get("fecha")).date() if data_previa.get("fecha") else pd.Timestamp.now().date())
                    dest = st.text_input("Destinatario:", value=data_previa.get("dest", ""))
                    cargo = st.text_input("Cargo:", value=data_previa.get("cargo", "P R E S E N T E"))
                    f_ref = st.text_input("Folio Ref:", value=data_previa.get("folio", ""))

                with st.container(border=True):
                    st.markdown("**📝 Mensaje**")
                    v_cuerpo = data_previa.get("cuerpo", plantillas_maestras[tipo_p])
                    cuerpo_txt = st.text_area("Cuerpo:", value=v_cuerpo, height=150)
                    firm = st.text_input("Firma (Nombre):", value=data_previa.get("firma", "NOMBRE DEL DIRECTOR"))
                    cargo_firm = st.text_input("Cargo del Firmante:", value=data_previa.get("cargo_f", "DIRECTOR DE ALUMBRADO PÚBLICO"))
                    ccp = st.text_input("C.c.p.:", value=data_previa.get("ccp", "Archivo, Minutario."))

                h_membrete = st.toggle("🛰️ Modo Hoja Membretada", value=False)

            with c_preview:
                st.markdown("### 👁️ Vista Previa")
                c_final = cuerpo_txt.replace("[FOLIO]", f"**{f_ref}**" if f_ref else "**_______**")
                e_sup = "100px" if h_membrete else "20px"

                st.markdown(f"""
                <div style="background: white; color: black; padding: 40px; border: 1px solid #ddd; font-family: 'Arial'; line-height: 1.6; min-height: 550px;">
                    <div style="height: {e_sup};"></div>
                    <div style="text-align: right; font-weight: bold;">Toluca, México; a {f_oficio.strftime('%d/%m/%Y')}<br>Oficio: {n_oficio}</div><br>
                    <div style="text-align: left; font-weight: bold;">{dest.upper()}<br>{cargo.upper()}</div><br>
                    <div style="text-align: justify;"> {c_final} </div><br><br>
                    <div style="text-align: center;"><b>A T E N T A M E N T E</b><br><br><br>__________________________<br><b>{firm.upper()}</b><br>{cargo_firm.upper()}</div>
                    <div style="font-size: 10px; border-top: 1px solid #eee; margin-top: 20px;">C.c.p. {ccp}</div>
                </div>
                """, unsafe_allow_html=True)

                st.divider()
                b_save, b_pdf = st.columns(2)

                if b_save.button("💾 GUARDAR/ACTUALIZAR", use_container_width=True):
                    id_r = n_oficio.replace("/", "-")
                    st.session_state.db_oficios[id_r] = {
                        "num": n_oficio, "fecha": str(f_oficio), "dest": dest, 
                        "cargo": cargo, "folio": f_ref, "cuerpo": cuerpo_txt, 
                        "firma": firm, "cargo_f": cargo_firm, "ccp": ccp
                    }
                    with open(PATH_OFICIOS_DB, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.db_oficios, f, indent=4, ensure_ascii=False)
                    st.success("✅ Bóveda Actualizada."); time.sleep(1); st.rerun()

                if motor_pdf_listo:
                    pdf = FPDF(); pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=15)
                    if h_membrete: pdf.ln(40)
                    else: pdf.ln(10)
                    pdf.set_font("Arial", 'B', 11)
                    pdf.cell(0, 5, txt=f"Toluca, México; a {f_oficio.strftime('%d/%m/%Y')}", ln=True, align='R')
                    pdf.cell(0, 5, txt=f"Oficio No: {n_oficio}", ln=True, align='R')
                    pdf.ln(15); pdf.cell(0, 5, txt=dest.upper() if dest else "A QUIEN CORRESPONDA", ln=True)
                    pdf.cell(0, 5, txt=cargo.upper(), ln=True)
                    pdf.ln(15); pdf.set_font("Arial", '', 11)
                    c_pdf = cuerpo_txt.replace("[FOLIO]", f_ref)
                    pdf.multi_cell(0, 7, txt=c_pdf.encode('latin-1', 'replace').decode('latin-1'), align='J')
                    pdf.ln(25); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 5, txt="A T E N T A M E N T E", ln=True, align='C')
                    pdf.ln(20); pdf.cell(0, 5, txt="__________________________", ln=True, align='C')
                    pdf.cell(0, 5, txt=firm.upper(), ln=True, align='C')
                    pdf.cell(0, 5, txt=cargo_firm.upper(), ln=True, align='C')
                    pdf.set_y(-30); pdf.set_font("Arial", '', 8); pdf.cell(0, 5, txt=f"C.c.p. {ccp}", ln=True)
                    
                    pdf_data = pdf.output(dest='S').encode('latin-1', 'replace')
                    st.download_button(label="🚀 DESCARGAR OFICIO PDF", data=pdf_data, file_name=f"Oficio_{n_oficio.replace('/','-')}.pdf", mime="application/pdf", use_container_width=True)
                else:
                    st.error("❌ Función PDF no disponible.")

    elif st.session_state.menu == "SF5":
        st.title("🛡️ SF5 - Pre-procesador Universal Anti-Duplicados")
        
        files_sf5 = st.file_uploader("📂 Cargar archivos de reportes", type=["csv", "xlsx"], accept_multiple_files=True, key="multi_sf5_v25")

        if files_sf5:
            dfs = []
            for f in files_sf5:
                if f.name.endswith('.xlsx'):
                    df_f = pd.read_excel(f, dtype=str).fillna("")
                else:
                    df_f = pd.read_csv(f, encoding='latin-1', dtype=str).fillna("")
                df_f['ARCHIVO_ORIGEN'] = f.name
                dfs.append(df_f)
            
            df_total = pd.concat(dfs, ignore_index=True)
            
            def motor_gps_v25(fila_texto):
                texto = str(fila_texto).lower()
                numeros = re.findall(r'-?\d+\.\d{4,}', texto)
                if len(numeros) >= 2:
                    return str(fila_texto), float(numeros[0]), float(numeros[1])
                return str(fila_texto), None, None

            resultados = df_total.apply(lambda r: motor_gps_v25(" ".join(r.astype(str))), axis=1)
            col_gps = next((c for c in df_total.columns if any(p in str(c).lower() for p in ['gps', 'ubicacion', 'coord', 'lat'])), df_total.columns[0])
            
            df_total[col_gps] = [r[0] for r in resultados]
            df_total['lat_aux'] = [r[1] for r in resultados]
            df_total['lon_aux'] = [r[2] for r in resultados]
            df_total['Grupo_Duplicado'] = 0
            
            df_analisis = df_total.dropna(subset=['lat_aux', 'lon_aux']).reset_index(drop=True)

            if not df_analisis.empty:
                umbral = 3 / 111111.0
                coords = df_analisis[['lat_aux', 'lon_aux']].values
                marcador_duplicados = [0] * len(df_analisis) 
                
                color_id = 1
                for i in range(len(coords)):
                    if marcador_duplicados[i] != 0: continue
                    encontrado = False
                    for j in range(i + 1, len(coords)):
                        if np.linalg.norm(coords[i] - coords[j]) < umbral:
                            marcador_duplicados[j] = color_id
                            encontrado = True
                    if encontrado:
                        marcador_duplicados[i] = color_id
                        color_id += 1

                df_analisis['Grupo_Duplicado'] = marcador_duplicados
                
                indices_hoja1 = []
                grupos_ya_agregados = set()
                for idx, row in df_analisis.iterrows():
                    g_id = row['Grupo_Duplicado']
                    if g_id == 0 or g_id not in grupos_ya_agregados:
                        indices_hoja1.append(idx)
                        if g_id > 0: grupos_ya_agregados.add(g_id)
                
                df_hoja1 = df_analisis.loc[indices_hoja1].copy()
                df_hoja2 = df_analisis[df_analisis['Grupo_Duplicado'] > 0].copy()

                st.markdown("### 📈 Dashboard de Depuración SF5")
                m_cols = st.columns(5)
                cant_procesados, cant_en_conflicto = len(df_analisis), len(df_hoja2)
                cant_eliminados, cant_unicos = cant_procesados - len(df_hoja1), len(df_hoja1)
                
                metricas = [
                    ("🔍 PROCESADOS", cant_procesados, "#1f4e78"),
                    ("🚨 EN CONFLICTO", cant_en_conflicto, "#e67e22"),
                    ("🗑️ ELIMINADOS", cant_eliminados, "#95a5a6"),
                    ("✅ ÚNICOS (H1)", cant_unicos, "#28a745"),
                    ("⏱️ AHORRO EST.", f"{cant_eliminados * 5} min", "#dc3545")
                ]

                for col, (label, value, color) in zip(m_cols, metricas):
                    col.markdown(f"<div style='text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px; border-left: 5px solid {color};'><b style='font-size: 11px;'>{label}</b><br><span style='font-size: 18px;'>{value}</span></div>", unsafe_allow_html=True)

                output_sf5 = io.BytesIO()
                with pd.ExcelWriter(output_sf5, engine='openpyxl') as writer:
                    df_h1_final = df_hoja1.drop(columns=['lat_aux', 'lon_aux', 'Grupo_Duplicado'])
                    df_h1_final.to_excel(writer, index=False, sheet_name='PARA_MODULO_1')
                    df_hoja2.to_excel(writer, index=False, sheet_name='REPORTE_DUPLICADOS')

                st.write("---")
                st.download_button(label="🚀 DESCARGAR PRODUCTO FINAL v25", data=output_sf5.getvalue(), file_name="SF_PANGEA_DEPURADO.xlsx", use_container_width=True)

                if st.button("➡️ ENVIAR DATOS LIMPIOS AL GENERADOR DE RUTAS (SF1)", use_container_width=True, type="primary"):
                    st.session_state.df_transferido = df_hoja1.copy()
                    st.session_state.nombre_archivo_transferido = "DEPURADO_SF5.xlsx"
                    st.session_state.menu = "SF1"
                    st.rerun()
            else:
                st.error("No se detectaron coordenadas válidas en los archivos.")

    elif st.session_state.menu == "SF6":
        st.title("📦 SF6 - Sistema de Gestión de Almacén (DAP)")
        
        PIN_ALMACEN = "DAP-2026"
        LEYENDA_OFICIAL = "Este material es propiedad del Ayuntamiento de Toluca y se genera en la Dirección de Alumbrado Público"

        if "db_inventario" not in st.session_state:
            st.session_state.db_inventario = pd.DataFrame(STOCK_INICIAL)
        if "vales_historial" not in st.session_state:
            st.session_state.vales_historial = []
        if "carrito_vale" not in st.session_state:
            st.session_state.carrito_vale = []
        if "admin_auth" not in st.session_state:
            st.session_state.admin_auth = False

        tab_inv, tab_vales, tab_admin = st.tabs(["📊 Existencias y Resumen", "🚚 Salida (Vale Oficial)", "⚙️ Gestión Almacén"])

        # --- PESTAÑA 1: EXISTENCIAS Y RESUMEN ---
        with tab_inv:
            df_inv = st.session_state.db_inventario
            st.subheader("🚨 Dashboard de Inventario")
            
            criticos = len(df_inv[df_inv['Stock'] <= df_inv['Min']])
            
            c_met1, c_met2 = st.columns(2)
            c_met1.metric("📦 Materiales en Catálogo", len(df_inv))
            c_met2.metric("⚠️ Alertas de Stock Crítico", criticos, delta=-criticos, delta_color="inverse")

            st.write("### Inventario Actual de Materiales e Insumos")
            st.dataframe(df_inv, use_container_width=True, hide_index=True)
            
            if st.button("📄 GENERAR RESUMEN EJECUTIVO (EXCEL)", use_container_width=True):
                output_res = io.BytesIO()
                with pd.ExcelWriter(output_res, engine='openpyxl') as writer:
                    df_inv.to_excel(writer, index=False, sheet_name='Estado_Almacen')
                st.download_button(
                    label="📥 Descargar Reporte de Stock", 
                    data=output_res.getvalue(), 
                    file_name=f"Resumen_Almacen_{pd.Timestamp.now().strftime('%d-%m-%Y')}.xlsx", 
                    use_container_width=True
                )

        # --- PESTAÑA 2: SALIDA (VALE OFICIAL CON FIRMAS) ---
        with tab_vales:
            st.subheader("🧾 Generador de Vale de Salida Oficial")
            
            prox_folio_num = len(st.session_state.vales_historial) + 1
            folio_actual = f"DAP-{prox_folio_num}"
            
            # --- SECCIÓN A: ASIGNACIÓN DESTACADA DE BRIGADA ---
            st.markdown(
                """
                <div style='background-color: #eef4f8; padding: 15px; border-left: 6px solid #1f4e78; border-radius: 6px; margin-bottom: 15px;'>
                    <h4 style='margin:0; color: #1f4e78;'>🚚 ASIGNACIÓN DE UNIDAD / BRIGADA</h4>
                    <p style='margin:0; font-size:13px; color:#555;'>Seleccione la cuadrilla operativa responsable del traslado y aplicación del material.</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            col_bri_haz = st.columns([1.5, 2])
            with col_bri_haz[0]:
                bri_sel = st.selectbox(
                    "Seleccione Brigada Asignada:", 
                    [f"Brigada {i}" for i in range(1, 18)] + ["Personal de Mantenimiento Interno", "Cuadrilla de Alumbrado Especial"],
                    key="brigada_salida_vales"
                )
            with col_bri_haz[1]:
                st.info(f"Folio del Vale en Proceso: **{folio_actual}**")

            # --- SECCIÓN B: CAPTURA DE MATERIALES ---
            with st.container(border=True):
                st.markdown("**🛒 Adición de Materiales al Lote**")
                c2, c3 = st.columns([2, 1])
                mat_sel = c2.selectbox("Seleccione Insumo:", df_inv['Material'].tolist())
                can_sel = c3.number_input("Cantidad a Entregar:", min_value=1, step=1)
                
                if st.button("➕ Agregar Insumo al Carrito", use_container_width=True):
                    stock_real = df_inv.loc[df_inv['Material'] == mat_sel, 'Stock'].values[0]
                    if stock_real >= can_sel:
                        existe = False
                        for item in st.session_state.carrito_vale:
                            if item['Material'] == mat_sel:
                                if (item['Cantidad'] + can_sel) <= stock_real:
                                    item['Cantidad'] += can_sel
                                    existe = True
                                else:
                                    st.error("⚠️ La cantidad agregada supera las existencias físicas en el almacén.")
                                    existe = True
                        if not existe:
                            st.session_state.carrito_vale.append({
                                "Material": mat_sel, 
                                "Cantidad": can_sel, 
                                "Unidad": df_inv.loc[df_inv['Material'] == mat_sel, 'Unidad'].values[0]
                            })
                        st.toast(f"✅ {mat_sel} sumado al vale actual.")
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error(f"⚠️ No hay suficiente material disponible. Existencia actual: {stock_real}")

            # --- SECCIÓN C: OBSERVACIONES DIGITALES ---
            st.markdown("### 📝 Control y Notas de Entrega")
            obs_digital = st.text_area(
                "Observaciones del Responsable de Almacén (Se captura en sistema):", 
                placeholder="Ej: Material destinado a la rehabilitación de luminarias en San Martín Toltepec. Se entrega cable con empalmes de fábrica.",
                key="obs_responsable_entrega"
            )

            if st.session_state.carrito_vale:
                st.write("---")
                st.markdown("### **Resumen del Pedido Operativo:**")
                
                df_carrito = pd.DataFrame(st.session_state.carrito_vale)
                st.dataframe(df_carrito, use_container_width=True, hide_index=True)
                
                col_v1, col_v2 = st.columns(2)
                
                if col_v1.button("❌ Cancelar Vale Completo", use_container_width=True):
                    st.session_state.carrito_vale = []
                    st.rerun()
                
                # --- GENERACIÓN AVANZADA DEL PDF ADMINISTRATIVO ---
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                
                # Encabezados institucionales
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "AYUNTAMIENTO DE TOLUCA", ln=True, align='C')
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 8, "DIRECCIÓN DE ALUMBRADO PÚBLICO", ln=True, align='C')
                pdf.cell(0, 8, f"VALE OFICIAL DE SALIDA: {folio_actual}", ln=True, align='C')
                pdf.ln(8)
                
                # Metadatos del documento
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 6, f"Fecha y Hora de Emisión: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 6, f"UNIDAD/BRIGADA DESTINO: {bri_sel.upper()}", ln=True)
                pdf.ln(4)
                
                # Tabla oficial corregida y sin duplicados residuales
                pdf.set_fill_color(230, 235, 240)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(110, 8, " Descripcion del Material / Insumo", 1, 0, 'L', True)
                pdf.cell(36, 8, "Entregado", 1, 0, 'C', True)
                pdf.cell(22, 8, "Utilizado", 1, 0, 'C', True)
                pdf.cell(22, 8, "Devuelto", 1, 1, 'C', True)
                
                pdf.set_font("Arial", '', 10)
                for it in st.session_state.carrito_vale:
                    pdf.cell(110, 8, f" {str(it['Material'])}", 1, 0, 'L')
                    pdf.cell(36, 8, f"{it['Cantidad']} {it['Unidad']}", 1, 0, 'C')
                    pdf.cell(22, 8, "", 1, 0, 'C') # Celda para requisitar en campo a mano
                    pdf.cell(22, 8, "", 1, 1, 'C') # Celda para requisitar en campo a mano
                
                pdf.ln(6)
                
                # Bloque de observaciones digitales
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 6, "Observaciones del Responsable de Almacén (Sistema):", ln=True)
                pdf.set_font("Arial", '', 9)
                msg_obs = obs_digital if obs_digital.strip() else "Ninguna anotada en sistema al momento de la salida."
                pdf.multi_cell(0, 5, msg_obs.encode('latin-1', 'replace').decode('latin-1'), 1)
                pdf.ln(4)
                
                # Bloque de observaciones físicas para el destinatario
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 6, "Observaciones de la Brigada al Recibir (Llenar en Físico a Mano):", ln=True)
                pdf.set_fill_color(255, 255, 255)
                # Creamos un cuadro en blanco espacioso para que escriban a mano
                pdf.cell(0, 18, "", 1, ln=True, fill=True)
                pdf.ln(15)
                
                # Leyenda de propiedad
                pdf.set_font("Arial", 'I', 9)
                pdf.multi_cell(0, 5, LEYENDA_OFICIAL, align='C')
                pdf.ln(15)
                
                # Distribución de las Firmas Oficiales abajo del documento
                y_pos_firmas = pdf.get_y()
                pdf.set_font("Arial", 'B', 9)
                
                # Columna de entrega (Almacén)
                pdf.set_xy(15, y_pos_firmas)
                pdf.cell(75, 4, "_____________________________________", ln=False, align='C')
                pdf.set_xy(15, y_pos_firmas + 4)
                pdf.cell(75, 4, "RESPONSABLE DE ENTREGA DE MATERIAL", ln=False, align='C')
                pdf.set_xy(15, y_pos_firmas + 8)
                pdf.set_font("Arial", '', 8)
                pdf.cell(75, 4, "(Firma y Sello de Almacén DAP)", ln=False, align='C')
                
                # Columna de recepción (Brigada)
                pdf.set_font("Arial", 'B', 9)
                pdf.set_xy(115, y_pos_firmas)
                pdf.cell(75, 4, "_____________________________________", ln=False, align='C')
                pdf.set_xy(115, y_pos_firmas + 4)
                pdf.cell(75, 4, "RESPONSABLE QUE RECIBE MATERIAL", ln=False, align='C')
                pdf.set_xy(115, y_pos_firmas + 8)
                pdf.set_font("Arial", '', 8)
                pdf.cell(75, 4, f"({bri_sel.upper()})", ln=False, align='C')
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
                
                if col_v2.download_button(
                    label=f"💾 EMITIR VALE Y DESCARGAR PDF ({folio_actual})",
                    data=pdf_bytes,
                    file_name=f"Vale_Oficial_Salida_{folio_actual}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                ):
                    for item in st.session_state.carrito_vale:
                        idx = df_inv[df_inv['Material'] == item['Material']].index[0]
                        st.session_state.db_inventario.at[idx, 'Stock'] -= item['Cantidad']
                    
                    # Se almacena el registro completo con desglose en la Bóveda
                    st.session_state.vales_historial.append({
                        "Folio": folio_actual, 
                        "Fecha": pd.Timestamp.now().strftime('%d/%m/%Y %H:%M'),
                        "Brigada": bri_sel,
                        "Materiales": list(st.session_state.carrito_vale), # Clonar estado del carrito
                        "Observaciones": obs_digital if obs_digital.strip() else "Sin observaciones"
                    })
                    st.session_state.carrito_vale = []
                    st.success(f"✅ Vale oficial {folio_actual} procesado y resguardado en Bóveda.")
                    time.sleep(0.5)
                    st.rerun()

        # --- PESTAÑA 3: GESTIÓN ALMACÉN (ENTRADAS) ---
        with tab_admin:
            st.subheader("⚙️ Panel de Control de Existencias")
            if not st.session_state.admin_auth:
                st.warning("🔒 Este apartado requiere clave de acceso de Almacén.")
                pass_in = st.text_input("🔑 Ingrese PIN de Almacén:", type="password")
                if st.button("🔓 Conceder Acceso"):
                    if pass_in == PIN_ALMACEN:
                        st.session_state.admin_auth = True
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta para el área DAP.")
            else:
                st.success("✅ Acceso de Administrador de Almacén Concedido")
                if st.button("🔒 Bloquear Panel de Gestión", type="secondary"):
                    st.session_state.admin_auth = False
                    st.rerun()
                
                st.divider()
                with st.form("entrada_stock"):
                    st.write("📥 **Ingresar Nuevo Lote (Abastecimiento de Almacén)**")
                    m_in = st.selectbox("Seleccione Material:", df_inv['Material'].tolist())
                    c_in = st.number_input("Cantidad Recibida:", min_value=1, step=1)
                    
                    if st.form_submit_button("✅ ACTUALIZAR INVENTARIO"):
                        idx = df_inv[df_inv['Material'] == m_in].index[0]
                        st.session_state.db_inventario.at[idx, 'Stock'] += c_in
                        st.success(f"📦 Entrada registrada. Stock actualizado de {m_in}: {st.session_state.db_inventario.at[idx, 'Stock']} unidades.")
                
                st.write("")
                st.markdown("---")
                st.subheader("🔒 Bóveda de Vales Emitidos (Historial Antirrobos)")
                st.caption("Registro histórico inmutable de salidas de material de la Dirección de Alumbrado Público.")

                if not st.session_state.vales_historial:
                    st.info("📂 La bóveda se encuentra vacía. No se han emitido vales oficiales en esta sesión.")
                else:
                    # Formatear la vista rápida usando .get() seguro para evitar KeyErrors
                    tabla_boveda = []
                    for v in st.session_state.vales_historial:
                        tabla_boveda.append({
                            "Folio": v["Folio"],
                            "Fecha/Hora": v.get("Fecha", "N/A"),
                            "Brigada / Destino": v["Brigada"],
                            "Total Insumos": len(v.get("Materiales", []))
                        })
                    
                    df_boveda = pd.DataFrame(tabla_boveda)
                    st.dataframe(df_boveda, use_container_width=True, hide_index=True)
                    
                    # Buscador e inspector individual de vales blindados
                    st.markdown("**🔍 Auditoría e Inspección de Folio**")
                    folios_disponibles = [v["Folio"] for v in st.session_state.vales_historial]
                    folio_select = st.selectbox("Seleccione Folio para auditoría interna:", folios_disponibles)
                    
                    # Recuperar datos del vale seleccionado
                    vale_auditado = next(item for item in st.session_state.vales_historial if item["Folio"] == folio_select)
                    
                    with st.container(border=True):
                        st.markdown(f"### 📄 Expediente: {vale_auditado['Folio']}")
                        st.write(f"**Fecha de Emisión:** {vale_auditado.get('Fecha', 'N/A')}")
                        st.write(f"**Asignado a:** {vale_auditado['Brigada']}")
                        st.write(f"**Notas de Almacén:** {vale_auditado.get('Observaciones', 'Sin notas registradas')}")
                        
                        st.write("**Desglose de Material Entregado:**")
                        lista_materiales = vale_auditado.get("Materiales", [])
                        if lista_materiales:
                            df_mat_auditoria = pd.DataFrame(lista_materiales)
                            st.dataframe(df_mat_auditoria, use_container_width=True, hide_index=True)
                        else:
                            st.warning("⚠️ Este vale corresponde a un registro antiguo sin desglose digital de materiales.")
