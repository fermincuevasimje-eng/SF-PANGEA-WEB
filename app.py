import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
import re, requests, unicodedata, simplekml, json
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SF PANGEA v4.5.0", layout="wide")

# --- VARIABLES CONSTANTES ---
BASE_COORDS = (19.291395219739588, -99.63555838631413)
T_UNIDAD_MIN, V_CIU = 20, 25
URL_MY_MAPS = "https://www.google.com/maps/d/u/0/"

# --- FUNCIONES DE LÓGICA PURA ---
def normalizar_texto(texto):
    if not isinstance(texto, str): texto = str(texto)
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto.lower()

def extraer_materiales(punto_dict, tipo):
    d_letras = {'un ':'1 ','uno ':'1 ','una ':'1 ','dos ':'2 ','tres ':'3 ','cuatro ':'4 ','cinco ':'5 '}
    posibles_cols = ['ASUNTO', 'Observaciones', 'asunto', 'observaciones', 'Asunto']
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

def generar_kml(df_ordenado, nombre_ruta):
    kml = simplekml.Kml()
    capa = kml.newfolder(name="SF PANGEA")
    for _, p in df_ordenado.iterrows():
        pnt = capa.newpoint(name=f"{p['ID_Pangea_Nombre']}", coords=[(p['lon_aux'], p['lat_aux'])])
        # Aquí se puede insertar la tabla HTML que ya tenías en tu script
        pnt.description = f"Punto: {p['No_Ruta']}\nLuminarias: {p['Cant_Luminarias']}"
    return kml.kml()

# --- INTERFAZ ---
st.title("🚀 SF PANGEA - Centro de Gestión Operativa")

# Pestañas: 1. Nueva Ruta, 2. Historial de Mapas
tab1, tab2 = st.tabs(["🆕 Generar Nueva Ruta", "📂 Historial y Descargas"])

with tab1:
    up = st.file_uploader("Cargar archivo de reporte", type=["csv", "xlsx"])
    if up:
        df_raw = pd.read_excel(up) if up.name.endswith('.xlsx') else pd.read_csv(up, encoding='latin1')
        
        # Detección GPS
        res_gps = df_raw.apply(lambda r: re.search(r'(-?\d+\.\d{4,})\s*,\s*(-?\d+\.\d{4,})', " ".join(r.astype(str))), axis=1)
        df_raw['lat_aux'] = res_gps.apply(lambda x: float(x.group(1)) if x else None)
        df_raw['lon_aux'] = res_gps.apply(lambda x: float(x.group(2)) if x else None)
        df_v = df_raw.dropna(subset=['lat_aux']).reset_index(drop=True)

        if not df_v.empty:
            # --- LÓGICA DE RUTA: INICIO EN PUNTO MÁS LEJANO (NO EN 0) ---
            pts = df_v.to_dict('records')
            # 1. Encontrar el punto 1 (el más lejano a la base)
            distancias_a_base = cdist([BASE_COORDS], np.array([[p['lat_aux'], p['lon_aux']] for p in pts]))[0]
            idx_lejano = np.argmax(distancias_a_base)
            
            # Comenzar la lista con el más lejano
            ordenados = [pts.pop(idx_lejano)]
            
            # Seguir con la lógica de proximidad desde ese punto
            while pts:
                restante_coords = np.array([[p['lat_aux'], p['lon_aux']] for p in pts])
                idx_proximo = np.argmin(cdist([(ordenados[-1]['lat_aux'], ordenados[-1]['lon_aux'])], restante_coords))
                ordenados.append(pts.pop(idx_proximo))
            
            df_final = pd.DataFrame(ordenados)
            for i, row in df_final.iterrows():
                df_final.at[i, 'No_Ruta'] = i + 1
                df_final.at[i, 'Cant_Luminarias'] = extraer_materiales(row, 'lum')
                df_final.at[i, 'ID_Pangea_Nombre'] = row.get('FOLIO', row.get('ID', 'S/N'))

            st.success(f"Ruta optimizada con {len(df_final)} puntos. El punto 1 es el más lejano a la base.")
            
            if st.button("💾 Guardar y Finalizar"):
                # Aquí conectaríamos con tu Google Sheets para guardar la referencia
                st.info("Ruta procesada. Ve a la pestaña 'Historial' para descargar.")

with tab2:
    st.subheader("📦 Repositorio de Rutas")
    # Simulación de menú de historial con buscador
    search = st.text_input("🔍 Buscar ruta por nombre o fecha...")
    
    # Ejemplo de cómo se vería una fila del menú
    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])
    with col1: st.write("📅 2026-04-07 | Ruta_Sauces_Sector_1")
    with col2: st.button("📥 KML", key="k1")
    with col3: st.button("📊 CSV", key="c1")
    with col4: st.button("📗 XLSX", key="x1")
    with col5: st.link_button("🌐 Ir a My Maps", URL_MY_MAPS)
