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
    {"ID": "LUM-01", "Material": "Luminaria LED 100W", "Stock": 150, "Min": 20, "Costo": 2500, "Unidad": "Pza"},
    {"ID": "FOT-02", "Material": "Fotocelda Universal", "Stock": 300, "Min": 50, "Costo": 180, "Unidad": "Pza"},
    {"ID": "CAB-03", "Material": "Cable Aluminio Neutra 2+1", "Stock": 5000, "Min": 500, "Costo": 45, "Unidad": "m"},
    {"ID": "BRA-04", "Material": "Brazo Galvanizado 1.5m", "Stock": 80, "Min": 15, "Costo": 650, "Unidad": "Pza"}
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
            max_puntos_ruta = st.slider("Puntos Máximos por Ruta (Segmentación):", 5, 50, 15)
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
                                st.rer
