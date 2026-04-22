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
        st.write("---")
        st.title(f"🛠️ Módulo SF3 - Gestión y Métricas")

        # Inicializar la llave de reset si no existe
        if "reset_key" not in st.session_state:
            st.session_state.reset_key = 0

        with st.expander("📝 REGISTRAR NUEVA ATENCIÓN (FORMULARIO)", expanded=True):
            # Usamos la reset_key para forzar la limpieza de los campos de arriba
            rk = st.session_state.reset_key
            
            # --- SECCIÓN A: IDENTIFICACIÓN Y UBICACIÓN ---
            c_f1, c_f2 = st.columns(2)
            with c_f1: f_fecha = st.date_input("1. Fecha de Atención", key=f"fecha_{rk}")
            with c_f2: f_ot = st.text_input("2. O.T.", key=f"ot_{rk}")

            f_calle = st.text_input("3. Calle", key=f"calle_{rk}")

            c_sel1, c_sel2 = st.columns(2)
            with c_sel1:
                f_del = st.selectbox("📍 4. Delegación", sorted(list(CATALOGO_MAESTRO.keys())), key=f"del_{rk}")
            with c_sel2:
                opciones_utb_f = sorted(CATALOGO_MAESTRO.get(f_del, []))
                f_utb = st.selectbox("🔍 5. UTB", opciones_utb_f, key=f"utb_{rk}")

            # --- SECCIÓN B: MÉTRICAS Y GUARDADO ---
            # El clear_on_submit=True limpia lo que está DENTRO del form
            with st.form("form_registro_sf3_reset", clear_on_submit=True):
                f_folio = st.text_input("6. Folio / Ticket / IMEI")

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
                    # 1. Guardar los datos
                    if "manual_db" not in st.session_state: st.session_state.manual_db = []
                    st.session_state.manual_db.append({
                        "FECHA": f_fecha.strftime("%d/%m/%Y"), "OT": f_ot.upper(), "CALLE": f_calle.upper(),
                        "DELEGACIÓN": f_del, "UTB": f_utb, "FOLIO": f_folio.upper(),
                        "REHAB": f_rehab, "MANTO": f_manto, "SUST": f_sust, "AMPLI": f_ampli, "OBS": f_obs
                    })
                    
                    # 2. El truco del Reset: Cambiamos la llave para limpiar los campos de afuera (1 al 5)
                    st.session_state.reset_key += 1
                    
                    # 3. Notificar y refrescar
                    st.toast(f"O.T. {f_ot} guardada. Formulario listo para nuevo registro.", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
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
                
                with c_input:
                    st.subheader("⌨️ Captura de Folios")
                    
                    # Formulario para capturar el Enter
                    with st.form("form_bajas", clear_on_submit=True):
                        col_f_in, col_r_in = st.columns(2)
                        with col_f_in:
                            in_f_val = st.text_input("Digite Folio/Ticket/IMEi:", key=f"f_{st.session_state.input_key}")
                        with col_r_in:
                            in_c_val = st.text_input("Respuesta 127 (Máx 30 car.):", max_chars=30, key=f"r_{st.session_state.input_key}")
                        
                        submitted = st.form_submit_button("➕ Agregar a Lista", use_container_width=True)
                        
                        if submitted:
                            f_final = in_f_val.strip()
                            c_final = in_c_val.strip() if in_c_val.strip() else "ATENDIDO"
                            
                            if f_final:
                                # --- CANDADO DE VALIDACIÓN PREMIUM ---
                                # Se busca el folio exactamente en la columna identificada del DataFrame de referencia
                                if f_final in df_ref[id_col_sf2].astype(str).values:
                                    st.session_state.lista_bajas[f_final] = c_final
                                    st.toast(f"Folio {f_final} validado", icon="✅")
                                    st.rerun()
                                else:
                                    st.error(f"⚠️ El folio '{f_final}' no existe en el archivo cargado. Verifique.")
                                # --------------------------------------
    
                    st.write("---")
                    if st.button("🗑️ Limpiar Lista Actual"):
                        st.session_state.lista_bajas = {}
                        st.rerun()
    
                with c_lista:
                    st.subheader("📋 Folios a dar de Baja")
                    if st.session_state.lista_bajas:
                        df_resumen_bajas = pd.DataFrame([{"Folio": k, "Respuesta 127": v} for k, v in st.session_state.lista_bajas.items()])
                        st.dataframe(df_resumen_bajas, use_container_width=True, hide_index=True)
                        
                        # Botón para procesar y descargar
                        if st.button("📥 Generar Documento de Bajas", use_container_width=True):
                            st.balloons()
                            
                            # Filtrar el dataframe original solo por los folios capturados
                            folios_a_buscar = list(st.session_state.lista_bajas.keys())
                            df_final_bajas = df_ref[df_ref[id_col_sf2].astype(str).isin(folios_a_buscar)].copy()
                            
                            # Agregar la columna Respuesta 127 mapeando desde el estado
                            df_final_bajas['RESPUESTA 127'] = df_final_bajas[id_col_sf2].map(st.session_state.lista_bajas)
                            
                            # Excel
                            output_sf2 = io.BytesIO()
                            with pd.ExcelWriter(output_sf2, engine='openpyxl') as writer:
                                df_final_bajas.to_excel(writer, index=False, sheet_name='BAJAS_SF')
                            
                            st.download_button(
                                label="📗 Descargar Excel de Bajas",
                                data=output_sf2.getvalue(),
                                file_name=f"BAJAS_{up_sf2.name}",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    else:
                        st.info("Esperando captura de folios...")
    
            except Exception as e:
                st.error(f"Error en SF2: {e}")
    
    elif st.session_state.menu == "SF1":
        st.title("🚀 GdR - Generador de Rutas")
        tab1, tab2, tab3 = st.tabs(["🆕 Nueva Ruta", "📂 Bitácora", "🗑️ Papelera"])

        with tab1:
            if st.session_state.perfil == "CONSULTA":
                st.warning("⚠️ Modo Consulta activo.")
            else:
                up = st.file_uploader("Subir Archivo (Excel/CSV)", type=["csv", "xlsx"])
                if up:
                    try:
                        df_raw = pd.read_excel(up, dtype=str).fillna("") if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin-1', dtype=str).fillna("")
                        id_col = next((c for c in df_raw.columns if any(p in str(c).upper() for p in ['FOLIO','TICKET','ID'])), df_raw.columns[0])
                        res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
                        df_raw['lat_aux'], df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None), res_gps.apply(lambda x: float(x.group(2)) if x else None)
                        df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

                        if not df_v.empty:
                            pts = df_v.to_dict('records')
                            
                            # MOTOR DE OPTIMIZACIÓN
                            ordenados_temp = []
                            last_coord = BASE_COORDS
                            
                            while pts:
                                rest = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                                idx = np.argmin(cdist([last_coord], rest))
                                proximo_punto = pts.pop(idx)
                                ordenados_temp.append(proximo_punto)
                                last_coord = (proximo_punto['lat_aux'], proximo_punto['lon_aux'])

                            # CORRECCIÓN LOGÍSTICA: El punto 1 es el más lejano
                            ordenados = ordenados_temp[::-1]

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
                            m1.metric("📍 Puntos", len(ordenados))
                            m2.metric("💡 Luminarias", total_lums)
                            m3.metric("🏗️ Postes", total_postes)
                            m4.metric("🧶 Cable", f"{total_cable} m")
                            m5.metric("🛣️ Distancia", f"{round(dist_real_km, 2)} km")
                            m6.metric("⏱️ Tiempo Est.", tiempo_abreviado)
                            st.write("---")

                            df_f = pd.DataFrame(ordenados)
                            cols_vits = ['No_Ruta', 'ID_Pangea_Nombre', 'Cant_Luminarias', 'Cant_Postes', 'Cant_Cable_m', 'Maps']
                            cols_orig = [c for c in df_raw.columns if c not in ['lat_aux', 'lon_aux']]
                            cols_extra_a_quitar = ['ï»¿No_Ruta', 'Maps']
                            columnas_finales = cols_vits + [c for c in cols_orig if c != id_col and c not in cols_extra_a_quitar]
                            df_export = df_f[columnas_finales]

                            st.success(f"✅ Ruta optimizada con éxito.")
                            c1, c2, c3, c4 = st.columns(4)

                            # --- EXCEL PRO DINÁMICO ---
                            buf_xlsx = io.BytesIO()
                            with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
                                df_export.to_excel(writer, index=False, sheet_name='Ruta')
                                ws = writer.sheets['Ruta']
                                last_row = len(ordenados) + 1
                                res_row = last_row + 2
                                ws.cell(row=res_row, column=2, value="--- RESUMEN OPERATIVO DINÁMICO ---")
                                ws.cell(row=res_row+1, column=1, value="Total Puntos:"); ws.cell(row=res_row+1, column=2, value=len(ordenados))
                                ws.cell(row=res_row+2, column=1, value="Total Luminarias:"); ws.cell(row=res_row+2, column=2, value=f"=SUM(C2:C{last_row})")
                                ws.cell(row=res_row+3, column=1, value="Total Postes:"); ws.cell(row=res_row+3, column=2, value=f"=SUM(D2:D{last_row})")
                                ws.cell(row=res_row+4, column=1, value="Total Cable:"); ws.cell(row=res_row+4, column=2, value=f"=SUM(E2:E{last_row})")
                                ws.cell(row=res_row+5, column=1, value="Distancia:"); ws.cell(row=res_row+5, column=2, value=f"{round(dist_real_km,2)} km")
                                f_calc_minutos = f"ROUND(((B{res_row+2}+B{res_row+3})*{t_por_punto})+({round(dist_real_km,2)}/{v_promedio}*60),0)"
                                ws.cell(row=res_row+6, column=1, value="Tiempo Estimado:")
                                ws.cell(row=res_row+6, column=2, value=f'=INT({f_calc_minutos}/60) & " h " & MOD({f_calc_minutos},60) & " m"')
                                
                                fg, fa = PatternFill(start_color="E2E2E2", end_color="E2E2E2", fill_type="solid"), PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
                                for r in range(2, last_row + 1):
                                    if int(df_f.iloc[r-2]['Cant_Postes']) > 0:
                                        for cell in ws[r]: cell.fill = fg
                                    elif int(df_f.iloc[r-2]['Cant_Cable_m']) > 0:
                                        for cell in ws[r]: cell.fill = fa

                            c1.download_button("📗 Excel Pro Dinámico", buf_xlsx.getvalue(), file_name=f"SF_{up.name}.xlsx", use_container_width=True)
                            
                            # CSV CORREGIDO
                            csv_buffer = io.StringIO()
                            df_export.to_csv(csv_buffer, index=False)
                            csv_buffer.write(f"\n--- RESUMEN OPERATIVO DINÁMICO ---\n")
                            csv_buffer.write(f"Total Puntos:,{len(ordenados)}\n")
                            csv_buffer.write(f"Total Luminarias:,{total_lums}\n")
                            csv_buffer.write(f"Total Postes:,{total_postes}\n")
                            csv_buffer.write(f"Total Cable:,{total_cable} m\n")
                            csv_buffer.write(f"Distancia Total:,{round(dist_real_km,2)} km\n")
                            csv_buffer.write(f"Tiempo Estimado:,{tiempo_abreviado}\n")
                            c2.download_button("📊 CSV Estático", csv_buffer.getvalue().encode('utf-8-sig'), file_name=f"SF_{up.name}.csv", use_container_width=True)

                            # --- KML MAESTRO PLANO ---
                            kml = simplekml.Kml()
                            for p in ordenados:
                                pnt = kml.newpoint(name=f"{p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
                                h = "<![CDATA[<table border='1' style='width:300px; border-collapse:collapse; font-family:Arial; font-size:12px;'>"
                                h += "<tr><td bgcolor='#767171' colspan='2' align='center'><b style='color:white;'>DATOS DEL REPORTE</b></td></tr>"
                                for col in cols_orig:
                                    val = str(p.get(col, '')).strip()
                                    if val: h += f"<tr><td bgcolor='#F2F2F2'><b>{col}:</b></td><td>{val}</td></tr>"
                                h += "<tr><td bgcolor='#1F4E78' colspan='2' align='center'><b style='color:white;'>DESGLOCE OPERATIVO</b></td></tr>"
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
                            
                            c3.download_button("🗺️ KML Maestro", kml.kml(), file_name=f"SF_{up.name}.kml", use_container_width=True)
                            c4.link_button("🚀 My Maps", "https://www.google.com/maps/d/", use_container_width=True)

                            if st.button("💾 REGISTRAR EN BITÁCORA", use_container_width=True):
                                try:
                                    conn = st.connection("gsheets", type=GSheetsConnection)
                                    hist = conn.read(spreadsheet=URL_DB, worksheet=HOJA_PRINCIPAL, ttl=0).dropna(how='all')
                                    info_j = f"Pts: {len(ordenados)}, Lums: {total_lums}, Cab: {total_cable}m, Dist: {round(dist_real_km,2)}km, T: {tiempo_abreviado}"
                                    n_f = pd.DataFrame([{"Fecha": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"), "Nombre_Ruta": up.name, "Usuario_Generador": st.session_state.usuario_nombre, "Datos_JSON": info_j}])
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
        st.write("---")                       # La raya ahora separa el menú del título
        st.title("🏗️ SF4 - Diseño de Procesos") 
        st.info("Bienvenido a la sección de diseño...")
        st.info("Bienvenido al Módulo de Diseño de Procesos.")
        st.write("Seleccione una herramienta para sistematizar actividades diarias.")
