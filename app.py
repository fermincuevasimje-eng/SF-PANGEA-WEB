import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, unicodedata, simplekml, io, requests, time, random, os, json, base64
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
    "SAN MATEO OTZACATIPAN": ['PONIENTE   I', 'PONIENTE  I I', 'RANCHO SAN JOSE', 'CANALEJA', 'ORIENTE  I', 'ORIENTE  II', 'LA MAGDALENA OTZACATIPAN', 'SANTA CRUZ OTZACATIPAN', 'SAN JOSE GUADALUPE OTZACATIPAN', 'SAN DIEGO DE LOS PADRES OTZACATIPAN', 'SAN BLAS OTZACATIPAN', 'SAN NICOLAS TOLENTINO  I', 'SAN NICOLAS TOLENTINO II', 'LA CRESPA', 'JARDINES DE LA CRESPA', 'GEOVILLAS ARBOLEDA', 'LA FLORESTA', 'GEOVILLAS DE LA INDEPENDENCIA', 'VICENTE LOMBARDO', 'ARBOLEDAS'],
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
    "SEMINARIO 2 DE MARZO": ['SEMINARIO 4A SECCION  I', 'SEMINARIO 4A SECCION II', 'HEROES 5 DE MAYO I', 'HEROES 5 DE MAYO II'],
    "SEMINARIO CONCILIAR": ['SEMINARIO EL PARQUE', 'SEMINARIO 3A SECCION', 'SEMINARIO 1A SECCION', 'SEMINARIO EL MODULO'],
    "SEMINARIO LAS TORRES": ['SEMINARIO SAN FELIPE DE JESUS', 'SEMINARIO 2A SECCION', 'SEMINARIO 5A SECCION'],
    "TECAXIC": ['TECAXIC ORIENTE', 'TECAXIC PONIENTE'],
    "TLACHALOYA": ['TLACHALOYA', 'BALBUENA', 'SAN CARLOS', 'SAN JOSE BUENAVISTA', 'DEL CENTRO', 'EL TEJOCOTE', 'SAN JOSE LA COSTA'],
    "UNIVERSIDAD": ['UNIVERSIDAD', 'CUAUHTEMOC', 'AMERICAS', 'ALTAMIRANO'],
}

# MAPA INVERSO PARA FUNCIONAMIENTO ÓPTIMO
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

# --- ESTADOS PARA EL MÓDULO SF4 (DISEÑO DE PROCESOS INTERACTIVO) ---
if "pasos_sf4" not in st.session_state:
    # Guardaremos una lista de diccionarios: [{'texto': '...', 'tipo': '...'}, ...]
    st.session_state.pasos_sf4 = [] 
if "edit_index" not in st.session_state:
    st.session_state.edit_index = -1

# --- PROTOCOLO DE PERSISTENCIA DE BÓVEDA ---
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
        if st.button("🚀 SF1-Generador de Rutas", use_container_width=True): 
                st.session_state.menu = "SF1"
            
        if st.button("📁 SF2-Bajas", use_container_width=True): 
                st.session_state.menu = "SF2"
            
        if st.button("📊 SF3-Captura y Métricas", use_container_width=True): 
                st.session_state.menu = "SF3"
                
        if st.button("🏗️ SF4-Diseño de Procesos", use_container_width=True): 
                st.session_state.menu = "SF4"

        if st.button("🛡️ SF5-Anti-Duplicados", use_container_width=True): 
                st.session_state.menu = "SF5"

        if st.button("📦 SF6-Almacén e Inventario", use_container_width=True): 
                st.session_state.menu = "SF6"
        st.write("---")
        if st.session_state.menu == "SF1":
            st.subheader("📊 Ajustes GdR")
            t_por_punto = st.slider("Minutos por Atención", 5, 60, 20)
            v_promedio = st.slider("Velocidad km/h", 10, 80, 25)
            st.write("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
        st.info("SF PANGEA V1")

# --- 5. CUERPO LÓGICO ---
    if st.session_state.menu == "Inicio":
        st.title("👋 Bienvenido a SF PANGEA")
        st.info("Sistema de Gestión Operativa - Dirección de Alumbrado Público")
        st.write("Seleccione un módulo en el menú lateral para comenzar.")
        st.image("https://img.icons8.com/clouds/500/000000/map-marker.png", width=150)

    elif st.session_state.menu == "SF3":
        st.title(f"🛠️ Módulo SF3 - Gestión y Métricas")

        # Inicialización de la llave de limpieza (Reset Key)
        if "reset_key" not in st.session_state:
            st.session_state.reset_key = 0
        
        rk = st.session_state.reset_key

        with st.expander("📝 REGISTRAR NUEVA ATENCIÓN (FORMULARIO)", expanded=False):
            # --- SELECCIÓN REACTIVA (FUERA DEL FORMULARIO) ---
            st.write("📍 **Paso 1: Ubicación**")
            col_geo1, col_geo2 = st.columns(2)
            with col_geo1:
                f_del = st.selectbox("Delegación", sorted(list(CATALOGO_MAESTRO.keys())), key=f"del_manual_{rk}")
            with col_geo2:
                opciones_utb_f = sorted(CATALOGO_MAESTRO.get(f_del, []))
                f_utb = st.selectbox("UTB", opciones_utb_f, key=f"utb_manual_{rk}")

            # --- FORMULARIO DE DATOS (DENTRO DEL FORMULARIO) ---
            with st.form(key=f"form_sf3_core_{rk}", clear_on_submit=True):
                st.write("📝 **Paso 2: Detalles de la Atención**")
                
                # FILA 1: Identificación
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1: f_fecha = st.date_input("Fecha")
                with c2: f_ot = st.text_input("O.T.")
                with c3: f_folio = st.text_input("Folio / Ticket / IMEI")
                
                f_calle = st.text_input("Calle")

                st.markdown("---")
                st.write("📊 **Cantidades de Trabajo Realizado:**")
                
                # FILA 4: Métricas
                m1, m2, m3, m4 = st.columns(4)
                with m1: f_rehab = st.number_input("7. Rehabilitación", min_value=0, step=1)
                with m2: f_manto = st.number_input("8. Mantenimiento", min_value=0, step=1)
                with m3: f_sust = st.number_input("9. Sustitución", min_value=0, step=1)
                with m4: f_ampli = st.number_input("10. Ampliación", min_value=0, step=1)

                # FILA 5: Notas finales
                f_obs = st.text_area("11. Observaciones")
                
                btn_guardar = st.form_submit_button("🚀 GUARDAR REGISTRO EN LISTA", use_container_width=True)

                if btn_guardar:
                    if "manual_db" not in st.session_state: st.session_state.manual_db = []
                    st.session_state.manual_db.append({
                        "FECHA": f_fecha.strftime("%d/%m/%Y"), "OT": f_ot.upper(), "CALLE": f_calle.upper(),
                        "DELEGACIÓN": f_del, "UTB": f_utb, "FOLIO": f_folio.upper(),
                        "REHAB": f_rehab, "MANTO": f_manto, "SUST": f_sust, "AMPLI": f_ampli, "OBS": f_obs
                    })
                    # Disparador del Reset y guardado exitoso
                    st.session_state.reset_key += 1
                    st.toast(f"O.T. {f_ot} registrada correctamente", icon="✅")
                    time.sleep(0.5)
                    st.rerun()

        if "manual_db" in st.session_state and st.session_state.manual_db:
            if st.button("🗑️ Borrar Último Registro Manual", use_container_width=True):
                st.session_state.manual_db.pop()
                st.rerun()

        st.markdown("---")
        
        # --- SECCIÓN DE ARCHIVO Y MÉTRICAS PERSISTENTES ---
        up_cap = st.file_uploader("📂 Opcional: Cargar Archivo de Captura Masiva", type=["csv", "xlsx"], key="up_cap_sf3")
        
        # Persistencia: Si hay archivo nuevo, se guarda en session_state para que no se borre al guardar manuales
        if up_cap:
            try:
                ext = 'xlsx' if up_cap.name.endswith('.xlsx') else 'csv'
                df_temp = load_massive_data(up_cap, ext)
                # Limpieza de cabeceras redundantes
                df_temp = df_temp[~df_temp.iloc[:, 0].astype(str).str.contains("IDENTIFICACION|CIUDADANO|JEFE", case=False, na=False)]
                st.session_state.masivo_pangea = df_temp
            except Exception as e:
                st.error(f"Error procesando archivo: {e}")

        # Inicialización de la memoria si está vacía
        if "masivo_pangea" not in st.session_state:
            st.session_state.masivo_pangea = None

        total_rehab, total_manto, total_sust, total_ampli = 0, 0, 0, 0
        
        # --- CONTROL MAESTRO DE FILTRADO (TUS SELECTORES ORIGINALES) ---
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

        piezas_reporte = []

        # 1. PROCESAR MANUAL (Si existe)
        if "manual_db" in st.session_state and st.session_state.manual_db:
            df_m = pd.DataFrame(st.session_state.manual_db)
            if sel_del != "TODAS": df_m = df_m[df_m['DELEGACIÓN'] == sel_del]
            if sel_utb != "TODAS": df_m = df_m[df_m['UTB'] == sel_utb]
            if not df_m.empty: piezas_reporte.append(df_m)

        # 2. PROCESAR MASIVO (Desde la memoria persistente)
        if st.session_state.masivo_pangea is not None:
            df_filt = st.session_state.masivo_pangea.copy()
            if sel_del != "TODAS": df_filt = df_filt[df_filt['del_norm'] == normalizar_texto(sel_del)]
            if sel_utb != "TODAS": df_filt = df_filt[df_filt['utb_norm'] == normalizar_texto(sel_utb)]
            
            if not df_filt.empty:
                df_archivo_v = df_filt.iloc[:, [4, 6, 15, 19, 22, 23, 29, 30, 31, 39]].copy()
                df_archivo_v.columns = ["FECHA", "OT", "FOLIO", "CALLE", "DELEGACIÓN", "UTB", "REHAB", "MANTO", "SUST", "AMPLI"]
                df_archivo_v["OBS"] = ""
                piezas_reporte.append(df_archivo_v)

        # 3. CONSOLIDACIÓN FINAL Y MÉTRICAS
        if piezas_reporte:
            df_final_vista = pd.concat(piezas_reporte, ignore_index=True)
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
            
            # --- FUNCIÓN SENIOR: EXCEL CON TOTALES Y GRÁFICA ---
            def generar_reporte_con_grafica(df_input, nombre_hoja):
                from openpyxl.chart import BarChart, Reference
                
                df_temp = df_input.copy()
                cols_n = ["REHAB", "MANTO", "SUST", "AMPLI"]
                for c in cols_n:
                    df_temp[c] = pd.to_numeric(df_temp[c], errors='coerce').fillna(0)
                
                # 1. Crear fila de Totales
                fila_tot = {col: "" for col in df_temp.columns}
                fila_tot["FECHA"] = "TOTALES"
                for c in cols_n: fila_tot[c] = df_temp[c].sum()
                df_reporte = pd.concat([df_temp, pd.DataFrame([fila_tot])], ignore_index=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_reporte.to_excel(writer, index=False, sheet_name=nombre_hoja)
                    wb = writer.book
                    ws = wb[nombre_hoja]
                    
                    # 2. Configurar Gráfica de Barras
                    chart = BarChart()
                    chart.type = "col"
                    chart.style = 10
                    chart.title = f"Resumen de Trabajo - {nombre_hoja}"
                    chart.y_axis.title = 'Cantidad'
                    chart.x_axis.title = 'Actividades'
                    
                    # Ubicar columnas de métricas para la gráfica
                    idx_inicio = df_reporte.columns.get_loc("REHAB") + 1
                    idx_fin = df_reporte.columns.get_loc("AMPLI") + 1
                    fila_totales = len(df_reporte) + 1
                    
                    # Datos (Fila de totales) y Categorías (Encabezados)
                    data = Reference(ws, min_col=idx_inicio, max_col=idx_fin, min_row=fila_totales, max_row=fila_totales)
                    cats = Reference(ws, min_col=idx_inicio, max_col=idx_fin, min_row=1, max_row=1)
                    
                    chart.add_data(data, titles_from_data=False)
                    chart.set_categories(cats)
                    ws.add_chart(chart, "M2") # Insertar a la derecha de los datos
                return output.getvalue()

            st.write("---")
            st.subheader("📥 Descargar Reportes con Gráficas")
            d_col1, d_col2, d_col3 = st.columns(3)

            # 1. BOTÓN REPORTE MASIVO
            if st.session_state.masivo_pangea is not None:
                df_m_f = st.session_state.masivo_pangea.copy()
                if sel_del != "TODAS": df_m_f = df_m_f[df_m_f['del_norm'] == normalizar_texto(sel_del)]
                if sel_utb != "TODAS": df_m_f = df_m_f[df_m_f['utb_norm'] == normalizar_texto(sel_utb)]
                if not df_m_f.empty:
                    df_m_out = df_m_f.iloc[:, [4, 6, 15, 19, 22, 23, 29, 30, 31, 39]].copy()
                    df_m_out.columns = ["FECHA", "OT", "FOLIO", "CALLE", "DELEGACIÓN", "UTB", "REHAB", "MANTO", "SUST", "AMPLI"]
                    xlsx_masivo = generar_reporte_con_grafica(df_m_out, "MASIVO")
                    d_col1.download_button("📂 Reporte MASIVO", xlsx_masivo, "REPORTE_MASIVO.xlsx", use_container_width=True)

            # 2. BOTÓN REPORTE MANUAL
            if "manual_db" in st.session_state and st.session_state.manual_db:
                df_man_f = pd.DataFrame(st.session_state.manual_db)
                if sel_del != "TODAS": df_man_f = df_man_f[df_man_f['DELEGACIÓN'] == sel_del]
                if sel_utb != "TODAS": df_man_f = df_man_f[df_man_f['UTB'] == sel_utb]
                if not df_man_f.empty:
                    xlsx_manual = generar_reporte_con_grafica(df_man_f, "MANUAL")
                    d_col2.download_button("📝 Reporte MANUAL", xlsx_manual, "REPORTE_MANUAL.xlsx", use_container_width=True)

            # 3. BOTÓN REPORTE UNIFICADO (COMPLETO)
            xlsx_unificado = generar_reporte_con_grafica(df_final_vista, "UNIFICADO")
            d_col3.download_button("🚀 Reporte UNIFICADO", xlsx_unificado, "REPORTE_UNIFICADO.xlsx", use_container_width=True)
    elif st.session_state.menu == "SF2":
        st.title("📁 SF2 - Módulo de Baja de Folios")
        st.write("Cargue el archivo original y digite los folios para generar el documento de cierre.")
        
        up_sf2 = st.file_uploader("Subir Archivo de Referencia (Excel/CSV)", type=["csv", "xlsx"], key="sf2_up")
        
        if up_sf2:
            try:
                df_ref = pd.read_excel(up_sf2, dtype=str).fillna("") if up_sf2.name.endswith('.xlsx') else pd.read_csv(up_sf2, encoding='latin-1', dtype=str).fillna("")
                
                # Identificar columna de folios
                id_col_sf2 = next((c for c in df_ref.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID','IMEI'])), df_ref.columns[0])
                
                c_input, c_lista = st.columns([1, 1])
                
                # =========================================================
                # COLUMNA IZQUIERDA: CAPTURA DE DATOS (FOCO REPARADO)
                # =========================================================
                with c_input:
                    st.subheader("⌨️ Captura de Folios")
                    
                    # El formulario cambia de ID dinámicamente con input_key para obligar al cursor a regresar arriba
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
                        
                        # --- MOTOR DE PROCESAMIENTO INMEDIATO ---
                        if submitted:
                            f_final = in_f_val.strip()
                            
                            if f_final:
                                # 1. Candado de Validación: Verificar existencia en archivo
                                if f_final in df_ref[id_col_sf2].astype(str).values:
                                    
                                    # 2. Formato estricto de fecha con año a 4 dígitos para Toluca (DD/MM/AAAA)
                                    if date_manual.strip():
                                        fecha_final_texto = date_manual.strip()
                                    else:
                                        fecha_final_texto = date_picker.strftime("%d/%m/%Y")
                                    
                                    # 3. Construcción de la respuesta
                                    ot_part = f"O.T. {in_ot_val.strip()}" if in_ot_val.strip() else ""
                                    libre_part = in_libre_val.strip()
                                    
                                    # REGLA MAESTRA: Si va vacío, auto-genera "ATENDIDO | FECHA"
                                    if not libre_part:
                                        componentes = [c for c in [ot_part, "ATENDIDO", fecha_final_texto] if c]
                                        c_final = " | ".join(componentes)
                                    else:
                                        # Si el usuario sí escribió observaciones, preserva todo lo capturado completo
                                        componentes = [c for c in [ot_part, fecha_final_texto, libre_part] if c]
                                        c_final = " | ".join(componentes)
                                    
                                    # Candado de longitud estricta para celdas de Excel (Máx 30 caracteres)
                                    if len(c_final) > 30:
                                        c_final = c_final[:27] + "..."
                                    
                                    # 4. Inyección en memoria limpia
                                    st.session_state.lista_bajas[f_final] = c_final
                                    st.toast(f"Folio {f_final} validado", icon="✅")
                                    
                                    # GATILLO DEL CURSOR: Cambiamos la llave maestra para reiniciar el formulario y regresar el foco al primer campo
                                    st.session_state.input_key += 1
                                    st.rerun()
                                else:
                                    st.error(f"⚠️ El folio '{f_final}' no existe en el archivo cargado. Verifique.")
                            else:
                                st.warning("⚠️ Por favor digite un folio antes de agregar.")

                # =========================================================
                # COLUMNA DERECHA: VISTAS, BÓVEDA Y EXCEL HISTÓRICO
                # =========================================================
                with c_lista:
                    # --- 1. GESTIÓN DE PERSISTENCIA (BÓVEDA FÍSICA) ---
                    PATH_BAJAS_DB = "boveda_bajas.json"
                    if "db_bajas_historico" not in st.session_state:
                        if os.path.exists(PATH_BAJAS_DB):
                            with open(PATH_BAJAS_DB, "r", encoding="utf-8") as f:
                                st.session_state.db_bajas_historico = json.load(f)
                        else:
                            st.session_state.db_bajas_historico = {}

                    # --- 2. INTERFAZ DE PESTAÑAS ---
                    tab_actual, tab_boveda = st.tabs(["📋 Captura Actual", "📂 Bóveda de Historial"])

                    with tab_actual:
                        st.subheader("Folios en proceso de baja")
                        if st.session_state.lista_bajas:
                            df_resumen_bajas = pd.DataFrame([{"Folio": k, "Respuesta 127": v} for k, v in st.session_state.lista_bajas.items()])
                            st.dataframe(df_resumen_bajas, use_container_width=True, hide_index=True)
                            
                            if st.button("📥 Generar Documento de Bajas", use_container_width=True, type="primary"):
                                st.balloons()
                                
                                folios_a_buscar = list(st.session_state.lista_bajas.keys())
                                df_final_bajas = df_ref[df_ref[id_col_sf2].astype(str).isin(folios_a_buscar)].copy()
                                
                                # ACOPLE DE TIRO SEGURO: Convertimos a String ambas partes para asegurar que no falle el mapeo en Excel
                                mapa_limpio = {str(key).strip(): str(val) for key, val in st.session_state.lista_bajas.items()}
                                df_final_bajas['RESPUESTA 127'] = df_final_bajas[id_col_sf2].astype(str).str.strip().map(mapa_limpio)
                                
                                output_sf2 = io.BytesIO()
                                with pd.ExcelWriter(output_sf2, engine='openpyxl') as writer:
                                    df_final_bajas.to_excel(writer, index=False, sheet_name='BAJAS_SF')
                                excel_data = output_sf2.getvalue()

                                # Protocolo de Respaldo en la Bóveda JSON
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
                                        df_detalles_hist = pd.DataFrame([{"Folio": k, "Respuesta 127": v} for k, v in data_hist["datos_capture"].items()])
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
        st.title("🚀 GdR - Generador de Rutas")
        tab1, tab2, tab3 = st.tabs(["🆕 Nueva Ruta", "📂 Bitácora", "🗑️ Papelera"])

        with tab1:
            if st.session_state.perfil == "CONSULTA":
                st.warning("⚠️ Modo Consulta activo.")
            else:
                # --- DETECCIÓN DE ORIGEN (ARCHIVO O TRANSFERENCIA) ---
                datos_vienen_de_sf5 = "df_transferido" in st.session_state and st.session_state.df_transferido is not None
                
                if datos_vienen_de_sf5:
                    st.info(f"📦 Usando datos procesados de: {st.session_state.nombre_archivo_transferido}")
                    if st.button("❌ Cancelar y subir otro archivo"):
                        st.session_state.df_transferido = None
                        st.rerun()
                    up = True # Gatillo para procesar
                else:
                    up = st.file_uploader("Subir Archivo (Excel/CSV)", type=["csv", "xlsx"])

                if up:
                    try:
                        if datos_vienen_de_sf5:
                            df_raw = st.session_state.df_transferido.copy()
                            up_name = st.session_state.nombre_archivo_transferido
                        else:
                            df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
                            up_name = up.name

                        id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                        res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                        df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
                        df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

                        if not df_v.empty:
                            pts = df_v.to_dict('records')
                            
                            # --- MOTOR DE OPTIMIZACIÓN V3 (ATRACCIÓN A BASE) ---
                            coords_base = np.array([BASE_COORDS])
                            coords_puntos = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                            distancias_a_base = cdist(coords_base, coords_puntos)[0]
                            
                            idx_mas_lejano = np.argmax(distancias_a_base)
                            punto_inicial = pts.pop(idx_mas_lejano)
                            ordenados = [punto_inicial]
                            last_coord = (punto_inicial['lat_aux'], punto_inicial['lon_aux'])

                            while pts:
                                rest_coords = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                                dist_al_ultimo = cdist([last_coord], rest_coords)[0]
                                dist_a_base = cdist(coords_base, rest_coords)[0]
                                puntuacion_ruta = dist_al_ultimo + (dist_a_base * 0.2)
                                
                                idx_proximo = np.argmin(puntuacion_ruta)
                                proximo_punto = pts.pop(idx_proximo)
                                ordenados.append(proximo_punto)
                                last_coord = (proximo_punto['lat_aux'], proximo_punto['lon_aux'])

                            # TRAZO VIAL
                            route_coords = [BASE_COORDS] + [(p['lat_aux'], p['lon_aux']) for p in ordenados] + [BASE_COORDS]
                            geo_trazo, dist_real_km = get_real_route(route_coords)
                            if not dist_real_km: 
                                dist_real_km = (len(ordenados) + 1) * 1.3
                                st.warning("🛰️ Servidor de rutas fuera de línea. El KML usará trazo directo.")

                            total_lums = 0; total_postes = 0; total_cable = 0
                            for i, p in enumerate(ordenados, 1):
                                p['No_Ruta'], p['ID_Pangea_Nombre'] = i, p[id_col]
                                p['Cant_Luminarias'] = extraer_carga_robusta(p, 'lum') or (1 if extraer_carga_robusta(p, 'poste')==0 and extraer_carga_robusta(p, 'cable')==0 else 0)
                                p['Cant_Postes'], p['Cant_Cable_m'] = extraer_carga_robusta(p, 'poste'), extraer_carga_robusta(p, 'cable')
                                p['Maps'] = f"https://www.google.com/maps?q={p['lat_aux']},{p['lon_aux']}"
                                total_lums += p['Cant_Luminarias']; total_postes += p['Cant_Postes']; total_cable += p['Cant_Cable_m']

                            min_totales = ((total_lums + total_postes) * t_por_punto) + (dist_real_km / v_promedio * 60)
                            tiempo_abreviado = f"{int(min_totales // 60)} h {int(min_totales % 60)} m"

                            # --- SECCIÓN: MÉTRICAS VISUALES ---
                            st.subheader("📊 Resumen de Carga de Trabajo")
                            m1, m2, m3, m4, m5, m6 = st.columns(6)
                            m1.metric("📍 Puntos", len(ordenados)); m2.metric("💡 Luminarias", total_lums)
                            m3.metric("🏗️ Postes", total_postes); m4.metric("🧶 Cable", f"{total_cable} m")
                            m5.metric("🛣️ Distancia", f"{round(dist_real_km, 2)} km"); m6.metric("⏱️ Tiempo Est.", tiempo_abreviado)
                            st.write("---")

                            df_f = pd.DataFrame(ordenados)
                            cols_vits = ['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']
                            cols_orig = [c for c in df_raw.columns if c not in ['lat_aux', 'lon_aux']]
                            columnas_finales = cols_vits + [c for c in cols_orig if c != id_col and c not in ['ï»¿No_Ruta', 'Maps']]
                            df_export = df_f[columnas_finales]

                            st.success(f"✅ Ruta optimizada con éxito.")
                            c1, c2, c3, c4 = st.columns(4)

                            # --- EXCEL PRO DINÁMICO (REPARADO CON TODAS LAS FILAS DE TOTALES) ---
                            buf_xlsx = io.BytesIO()
                            with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
                                df_export.to_excel(writer, index=False, sheet_name='Ruta')
                                ws = writer.sheets['Ruta']
                                last_row = len(ordenados) + 1
                                res_row = last_row + 2
                                # Encabezado del Resumen
                                ws.cell(row=res_row, column=2, value="--- RESUMEN OPERATIVO DINÁMICO ---")
                                # Filas de Totales
                                ws.cell(row=res_row+1, column=1, value="Total Puntos:"); ws.cell(row=res_row+1, column=2, value=len(ordenados))
                                ws.cell(row=res_row+2, column=1, value="Total Luminarias:"); ws.cell(row=res_row+2, column=2, value=f"=SUM(C2:C{last_row})")
                                ws.cell(row=res_row+3, column=1, value="Total Postes:"); ws.cell(row=res_row+3, column=2, value=f"=SUM(D2:D{last_row})")
                                ws.cell(row=res_row+4, column=1, value="Total Cable:"); ws.cell(row=res_row+4, column=2, value=f"=SUM(E2:E{last_row})")
                                ws.cell(row=res_row+5, column=1, value="Distancia:"); ws.cell(row=res_row+5, column=2, value=f"{round(dist_real_km,2)} km")
                                # Fórmula de Tiempo
                                f_calc = f"ROUND(((B{res_row+2}+B{res_row+3})*{t_por_punto})+({round(dist_real_km,2)}/{v_promedio}*60),0)"
                                ws.cell(row=res_row+6, column=1, value="Tiempo Estimado:")
                                ws.cell(row=res_row+6, column=2, value=f'=INT({f_calc}/60) & " h " & MOD({f_calc},60) & " m"')
                                
                                # Coloreado de Filas
                                fg, fa = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid"), PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
                                for r in range(2, last_row + 1):
                                    if int(df_f.iloc[r-2]['Cant_Postes']) > 0:
                                        for cell in ws[r]: cell.fill = fg
                                    elif int(df_f.iloc[r-2]['Cant_Cable_m']) > 0:
                                        for cell in ws[r]: cell.fill = fa

                            c1.download_button("📗 Excel Pro Dinámico", buf_xlsx.getvalue(), file_name=f"SF_{up_name}.xlsx", use_container_width=True)
                            
                            # --- CSV ---
                            csv_buffer = io.StringIO()
                            df_export.to_csv(csv_buffer, index=False)
                            # Resumen en CSV
                            csv_buffer.write(f"\n--- RESUMEN OPERATIVO DINÁMICO ---\n")
                            csv_buffer.write(f"Total Puntos:,{len(ordenados)}\n")
                            csv_buffer.write(f"Total Luminarias:,{total_lums}\n")
                            csv_buffer.write(f"Total Postes:,{total_postes}\n")
                            csv_buffer.write(f"Total Cable:,{total_cable} m\n")
                            csv_buffer.write(f"Distancia Total:,{round(dist_real_km,2)} km\n")
                            csv_buffer.write(f"Tiempo Estimado:,{tiempo_abreviado}\n")
                            c2.download_button("📊 CSV Estático", csv_buffer.getvalue().encode('utf-8-sig'), file_name=f"SF_{up_name}.csv", use_container_width=True)

                            # --- KML MAESTRO (REPARADO: TABLA HTML COMPLETA Y DESGLOSE) ---
                            kml = simplekml.Kml()
                            for p in ordenados:
                                pnt = kml.newpoint(name=f"{p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
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
                                h += "<tr><td bgcolor='#C00000' colspan='2' align='center'><b style='color:white;'>RESUMEN OPERATIVO DINÁMICO</b></td></tr>"
                                h += f"<tr><td><b>Total Puntos:</b></td><td>{len(ordenados)}</td></tr>"
                                h += f"<tr><td><b>Total Luminarias Ruta:</b></td><td>{total_lums}</td></tr>"
                                h += f"<tr><td><b>Total Postes Ruta:</b></td><td>{total_postes}</td></tr>"
                                h += f"<tr><td><b>Total Cable Ruta:</b></td><td>{total_cable} m</td></tr>"
                                h += f"<tr><td><b>Distancia Total:</b></td><td>{round(dist_real_km,2)} km</td></tr>"
                                h += f"<tr><td><b>Tiempo Est.:</b></td><td>{tiempo_abreviado}</td></tr>"
                                h += "</table>]]>"
                                pnt.description = h

                            if geo_trazo:
                                ls_coords = [(float(c[0]), float(c[1])) for c in geo_trazo]
                                ls = kml.newlinestring(name="TRAYECTO VIAL COMPLETO (BASE-RUTA-BASE)")
                                ls.coords = ls_coords
                                ls.style.linestyle.width = 6
                                ls.style.linestyle.color = 'ff0000ff'
                            else:
                                ls = kml.newlinestring(name="TRAYECTO DIRECTO (SIN CALLES)")
                                ls.coords = [(float(c[1]), float(c[0])) for c in route_coords]
                                ls.style.linestyle.width = 4
                                ls.style.linestyle.color = 'ff00ffff'

                            c3.download_button("🗺️ KML Maestro", kml.kml(), file_name=f"SF_{up_name}.kml", use_container_width=True)
                            c4.link_button("🚀 My Maps", "https://www.google.com/maps/d/", use_container_width=True)

                            # --- BITÁCORA ---
                            if st.button("💾 REGISTRAR EN BITÁCORA", use_container_width=True):
                                try:
                                    conn = st.connection("gsheets", type=GSheetsConnection)
                                    hist = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                                    info_j = f"Pts: {len(ordenados)}, Lums: {total_lums}, Cab: {total_cable}m, Dist: {round(dist_real_km,2)}km, T: {tiempo_abreviado}"
                                    n_f = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Nombre_Ruta": up_name, "Usuario_Generador": st.session_state.usuario_nombre, "Datos_JSON": info_j}])
                                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=pd.concat([hist, n_f], ignore_index=True))
                                    st.balloons(); st.success("¡Bitácora actualizada!")
                                except Exception as e: st.error(f"Error GSheets: {e}")

                    except Exception as e: st.error(f"Error procesando archivo: {e}")

        with tab2: # BITÁCORA
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_bt = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                if not df_bt.empty:
                    df_bt_v = df_bt.copy()
                    df_bt_v.insert(0, "ID_Reg", range(1, len(df_bt_v) + 1))
                    if st.session_state.perfil == "ADMIN":
                        c_sel, c_del = st.columns([3, 1])
                        with c_sel: ids_e = st.multiselect("ID para mover a papelera:", df_bt_v["ID_Reg"].tolist())
                        with c_del:
                            if st.button("🗑️ Mover"):
                                if ids_e:
                                    idx_e = df_bt_v[df_bt_v["ID_Reg"].isin(ids_e)].index
                                    df_tr = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, ttl=0).dropna(how='all')
                                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PAPELERA, data=pd.concat([df_tr, df_bt.loc[idx_e]], ignore_index=True))
                                    conn.update(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, data=df_bt.drop(idx_e))
                                    st.success("Movido."); time.sleep(1); st.rerun()
                    st.dataframe(df_bt_v.sort_values("ID_Reg", ascending=False), hide_index=True, use_container_width=True)
                else: st.info("Bitácora vacía.")
            except: st.info("Sincronizando...")

        with tab3: # PAPELERA MEJORADA
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
                    else: st.info("Papelera vacía.")
                except: st.info("Cargando papelera...")

    elif st.session_state.menu == "SF4":
        st.title("🏗️ SF4 - Arquitecto de Procesos & Oficios")
        
        tab_c, tab_b, tab_i, tab_o = st.tabs([
            "🆕 Constructor Inteligente", 
            "🗄️ Bóveda de Proyectos", 
            "📥 Importación Externa", 
            "📄 GENERADOR DE OFICIOS"
        ])

        with tab_c:
            # --- 1. CAPTURA INTELIGENTE (TU LÓGICA ORIGINAL) ---
            with st.expander("📝 CONFIGURAR PASO", expanded=True):
                idx = st.session_state.edit_index
                editando = (idx != -1)
                paso_actual = st.session_state.pasos_sf4[idx] if editando else {}
                form_key = f"sf4_f_{len(st.session_state.pasos_sf4)}_{idx}"
                
                txt = st.text_input("Actividad o Pregunta (usa '?' para bifurcar):", 
                                   value=paso_actual.get('texto', ""), key=f"txt_{form_key}")
                
                is_decision = txt.strip().endswith('?')
                destinos = ["Siguiente", "Fin"] + [f"Paso {i+1}" for i in range(len(st.session_state.pasos_sf4))]

                c1, c2, c3 = st.columns(3)
                if not is_decision:
                    with c1: 
                        tipo = st.selectbox("Forma:", ["Proceso", "Inicio/Fin"], 
                                          index=0 if paso_actual.get('tipo') == "Proceso" else (1 if paso_actual.get('tipo') == "Inicio/Fin" else 0))
                    with c2: 
                        d_val = paso_actual.get('conecta_a', "Siguiente")
                        destino = st.selectbox("Conecta a:", destinos, index=destinos.index(d_val) if d_val in destinos else 0)
                    with c3: 
                        label = st.text_input("Etiqueta flecha:", value=paso_actual.get('etiqueta_flecha', ""), placeholder="Ej: Ok")
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

            # --- 2. VISTA DIVIDIDA Y MOTOR (TU LÓGICA ORIGINAL) ---
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
                    mmd_nodos = []
                    mmd_conexiones = []

                    for i, p in enumerate(st.session_state.pasos_sf4):
                        id_n = f"N{i}"
                        t_c = clean(p.get('texto', ''))
                        if p.get('tipo') == "Decisión": mmd_nodos.append(f'    {id_n}{{"{t_c}"}}:::decision')
                        elif p.get('tipo') == "Inicio/Fin": mmd_nodos.append(f'    {id_n}(("{t_c}"))')
                        else: mmd_nodos.append(f'    {id_n}["{t_c}"]:::proceso')

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
            raw_import = st.text_area("Pega el código Mermaid aquí:", height=300, key="area_import_sf", 
                                     placeholder="graph TD\nN0((\"Inicio\")) --> N1[\"Proceso\"]")
            
            if st.button("🚀 REDISEÑAR PROCESO", use_container_width=True):
                if raw_import:
                    try:
                        nuevos_pasos = []
                        # Limpiamos y dividimos el código por líneas
                        lineas = [l.strip() for l in raw_import.split('\n') if l.strip()]
                        
                        # Buscamos definiciones de nodos: N0((Texto)), N1[Texto], N2{Texto}
                        for linea in lineas:
                            # 1. Detectar Inicio/Fin (( ))
                            m_io = re.search(r'(\w+)\(\("(.+?)"\)\)', linea)
                            if m_io:
                                nuevos_pasos.append({"texto": m_io.group(2), "tipo": "Inicio/Fin", "is_decision": False, "conecta_a": "Siguiente", "etiqueta_flecha": ""})
                                continue
                            
                            # 2. Detectar Decisiones { }
                            m_dec = re.search(r'(\w+)\{"(.+?)"\}', linea)
                            if m_dec:
                                nuevos_pasos.append({"texto": m_dec.group(2) + "?", "tipo": "Decisión", "is_decision": True, "label_si": "SÍ", "dest_si": "Siguiente", "label_no": "NO", "dest_no": "Fin"})
                                continue

                            # 3. Detectar Procesos [ ]
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

        # --- 📄 PESTAÑA: GENERADOR DE OFICIOS (VERSIÓN PROFESIONAL GRP V2.2 - REPARADA) ---
        with tab_o:
            st.subheader("📄 Correspondencia Oficial y Control de Bóveda")
            PATH_OFICIOS_DB = "boveda_oficios.json"

            # A. VALIDACIÓN DE MOTOR PDF (Protocolo Antibloqueo)
            try:
                from fpdf import FPDF
                motor_pdf_listo = True
            except ImportError:
                motor_pdf_listo = False
                st.warning("⚠️ Motor PDF (fpdf) no detectado. Las descargas están deshabilitadas.")

            # B. MOTOR DE PERSISTENCIA
            if "db_oficios" not in st.session_state:
                if os.path.exists(PATH_OFICIOS_DB):
                    with open(PATH_OFICIOS_DB, "r", encoding="utf-8") as f:
                        st.session_state.db_oficios = json.load(f)
                else:
                    st.session_state.db_oficios = {}

            plantillas_maestras = {
                "✅ Atención Exitosa": "Por medio de la presente, se hace de su conocimiento que la petición con folio [FOLIO] ha sido atendida exitosamente por las brigadas de esta Dirección, quedando el servicio en óptimas condiciones de operación.",
                "💡 Ya en Servicio": "Tras la inspección realizada por el personal técnico, se hace de su conocimiento que la luminaria correspondiente al folio [FOLIO] ya se encuentra en servicio y funcionando correctamente.",
                "⏳ Programado/Parcial": "Se informa que la atención al folio [FOLIO] se encuentra en estado parcial; los trabajos continuarán conforme a la disponibilidad de material especializado en el programa de mantenimiento.",
                "🔌 Bajadas de Luz": "Se autoriza la maniobra de bajada de luz solicitada mediante el folio [FOLIO], misma que será coordinada por el personal asignado a la zona correspondiente.",
                "❌ Atención Negativa": "Respecto a la petición [FOLIO], se informa que tras el análisis técnico, la solicitud ha sido determinada como improcedente debido a restricciones normativas o técnicas vigentes."
            }

            # 2. INTERFAZ DE CONTROL
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
                    <div style="text-align: center;"><b>A T E N T A M E N T E</b><br><br><br>__________________________<br><b>{firm.upper()}</b></div>
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
                    # PROCESAMIENTO PDF
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

# === INICIO MÓDULO SF5 V25 CORREGIDO (MOTOR AGNOSTICO) ===
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
                    lat, lon = float(numeros[0]), float(numeros[1])
                    limpio = str(fila_texto)
                    for basura in ["latitude:", "longitude:", "lat:", "long:", "latitud:", "longitud:", "gps:"]:
                        limpio = re.sub(re.escape(basura), "", limpio, flags=re.IGNORECASE)
                    return limpio.strip(), lat, lon
                return str(fila_texto), None, None

            resultados = df_total.apply(lambda r: motor_gps_v25(" ".join(r.astype(str))), axis=1)
            col_gps = next((c for c in df_total.columns if any(p in str(c).lower() for p in ['gps', 'ubicacion', 'coord', 'lat'])), df_total.columns[0])
            
            df_total[col_gps] = [r[0] for r in resultados]
            df_total['lat_aux'] = [r[1] for r in resultados]
            df_total['lon_aux'] = [r[2] for r in resultados]
            
            df_analisis = df_total.dropna(subset=['lat_aux', 'lon_aux']).reset_index(drop=True)

            if not df_analisis.empty:
                # MOTOR DE PROXIMIDAD (3 METROS)
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

    # === MÓDULO SF6: ALMACÉN E INVENTARIO V21.3 (FUNCIONALIDAD COMPLETA) ===
    elif st.session_state.menu == "SF6":
        st.title("📦 SF6 - Sistema de Gestión de Almacén (DAP)")
        
        # CONFIGURACIÓN
        PIN_ALMACEN = "DAP-2026"
        LEYENDA_OFICIAL = "Este material es propiedad del Ayuntamiento y se genera en la Dirección de Alumbrado Público"

        # INICIALIZACIÓN DE ESTADOS
        if "db_inventario" not in st.session_state:
            st.session_state.db_inventario = pd.DataFrame(STOCK_INICIAL)
        if "vales_historial" not in st.session_state:
            st.session_state.vales_historial = []
        if "carrito_vale" not in st.session_state:
            st.session_state.carrito_vale = []
        if "admin_auth" not in st.session_state:
            st.session_state.admin_auth = False

        tab_inv, tab_vales, tab_admin = st.tabs(["📊 Existencias y Resumen", "🚚 Salida (Vale)", "⚙️ Gestión Almacén"])

        # --- TAB 1: EXISTENCIAS Y RESUMEN EJECUTIVO ---
        with tab_inv:
            df_inv = st.session_state.db_inventario
            st.subheader("🚨 Dashboard de Inventario")
            
            # Métricas Restauradas
            m1, m2, m3 = st.columns(3)
            criticos = len(df_inv[df_inv['Stock'] <= df_inv['Min']])
            m1.metric("📦 Items Totales", len(df_inv))
            m2.metric("⚠️ Stock Crítico", criticos, delta=-criticos, delta_color="inverse")
            m3.metric("💰 Valor Almacén", f"${(df_inv['Stock'] * df_inv['Costo']).sum():,.2f}")

            st.dataframe(df_inv.style.apply(lambda r: ['background-color: #ffcccc' if r.Stock <= r.Min else '' for _ in r], axis=1), 
                         use_container_width=True, hide_index=True)
            
            # Botón Resumen Ejecutivo
            if st.button("📄 GENERAR RESUMEN EJECUTIVO (EXCEL)", use_container_width=True):
                output_res = io.BytesIO()
                with pd.ExcelWriter(output_res, engine='openpyxl') as writer:
                    df_inv.to_excel(writer, index=False, sheet_name='Estado_Almacen')
                st.download_button("📥 Descargar Reporte de Stock", output_res.getvalue(), f"Resumen_Almacen_{pd.Timestamp.now().strftime('%d_%m_%Y')}.xlsx", use_container_width=True)

        # --- TAB 2: VALE MULTI-ÍTEM CON FOLIO CONSECUTIVO ---
        with tab_vales:
            st.subheader("🧾 Generador de Vale de Salida")
            
            # Cálculo de Folio Consecutivo
            prox_folio_num = len(st.session_state.vales_historial) + 1
            folio_actual = f"DAP-{prox_folio_num}"
            st.info(f"Próximo Folio a Generar: **{folio_actual}**")

            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                bri_sel = c1.selectbox("Brigada Destino:", [f"Brigada {i}" for i in range(1, 18)])
                mat_sel = c2.selectbox("Material:", df_inv['Material'].tolist())
                can_sel = c3.number_input("Cantidad:", min_value=1, step=1)
                
                if st.button("➕ Agregar al Vale"):
                    stock_real = df_inv.loc[df_inv['Material'] == mat_sel, 'Stock'].values[0]
                    if stock_real >= can_sel:
                        st.session_state.carrito_vale.append({
                            "Material": mat_sel, 
                            "Cantidad": can_sel, 
                            "Unidad": df_inv.loc[df_inv['Material'] == mat_sel, 'Unidad'].values[0]
                        })
                        st.toast(f"{mat_sel} agregado.")
                    else:
                        st.error(f"⚠️ Stock insuficiente ({stock_real} disponibles).")

            if st.session_state.carrito_vale:
                st.write("---")
                st.markdown("**Pre-visualización del Vale:**")
                
                # Tabla con opción de eliminar material individualmente
                for i, it in enumerate(st.session_state.carrito_vale):
                    col_item, col_del = st.columns([4, 1])
                    col_item.write(f"• {it['Material']} - {it['Cantidad']} {it['Unidad']}")
                    if col_del.button("🗑️", key=f"del_it_{i}"):
                        st.session_state.carrito_vale.pop(i)
                        st.rerun()
                
                col_v1, col_v2 = st.columns(2)
                if col_v1.button("❌ Cancelar Todo", use_container_width=True):
                    st.session_state.carrito_vale = []
                    st.rerun()
                
                if col_v2.button("💾 REGISTRAR Y GENERAR PDF", type="primary", use_container_width=True):
                    # 1. Descuento de Stock
                    for item in st.session_state.carrito_vale:
                        idx = df_inv[df_inv['Material'] == item['Material']].index[0]
                        st.session_state.db_inventario.at[idx, 'Stock'] -= item['Cantidad']
                    
                    # 2. Guardar en Historial (para el consecutivo)
                    st.session_state.vales_historial.append({"Folio": folio_actual, "Brigada": bri_sel})

                    # 3. PDF Formal
                    from fpdf import FPDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 10, "AYUNTAMIENTO DE TOLUCA", ln=True, align='C')
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, "DIRECCIÓN DE ALUMBRADO PÚBLICO", ln=True, align='C')
                    pdf.cell(0, 10, f"VALE DE SALIDA: {folio_actual}", ln=True, align='C')
                    pdf.ln(10)
                    pdf.set_font("Arial", '', 10)
                    pdf.cell(0, 10, f"Fecha: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')} | Brigada: {bri_sel}", ln=True)
                    
                    # Tabla de materiales
                    pdf.set_fill_color(230, 230, 230)
                    pdf.cell(100, 8, "Material", 1, 0, 'C', True)
                    pdf.cell(30, 8, "Cantidad", 1, 1, 'C', True)
                    for it in st.session_state.carrito_vale:
                        pdf.cell(100, 8, str(it['Material']), 1)
                        pdf.cell(30, 8, str(it['Cantidad']), 1, 1, 'C')
                    
                    pdf.ln(10)
                    pdf.set_font("Arial", 'I', 9)
                    pdf.multi_cell(0, 5, LEYENDA_OFICIAL, align='C')
                    
                    pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
                    st.download_button(f"📥 DESCARGAR {folio_actual}", pdf_bytes, f"Vale_{folio_actual}.pdf", "application/pdf", use_container_width=True)
                    
                    st.session_state.carrito_vale = []
                    st.success(f"Vale {folio_actual} procesado.")

        # --- TAB 3: ADMIN (CANDADO DE SEGURIDAD) ---
        with tab_admin:
            st.subheader("⚙️ Gestión de Almacén")
            
            if not st.session_state.admin_auth:
                st.warning("Se requiere autorización para modificar el inventario.")
                pass_in = st.text_input("🔑 Ingrese Clave de Acceso:", type="password")
                if st.button("🔓 Desbloquear Gestión"):
                    if pass_in == PIN_ALMACEN:
                        st.session_state.admin_auth = True
                        st.rerun()
                    else:
                        st.error("Clave incorrecta.")
            else:
                st.success("✅ Modo Administrador Activo")
                if st.button("🔒 Cerrar Sesión de Gestión", type="secondary"):
                    st.session_state.admin_auth = False
                    st.rerun()
                
                st.divider()
                with st.form("entrada_stock"):
                    st.write("📥 **Registrar Entrada de Material**")
                    m_in = st.selectbox("Material:", df_inv['Material'].tolist())
                    c_in = st.number_input("Cantidad:", min_value=1, step=1)
                    if st.form_submit_button("✅ ACTUALIZAR STOCK"):
                        idx = df_inv[df_inv['Material'] == m_in].index[0]
                        st.session_state.db_inventario.at[idx, 'Stock'] += c_in
                        st.success(f"Stock de {m_in} actualizado.")
