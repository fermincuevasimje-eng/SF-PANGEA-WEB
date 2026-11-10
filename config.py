# config.py
# Sin credenciales en el código: los PINs viven en Streamlit Secrets ([pins]).
# Ver .streamlit/secrets.toml.example. Sin Secrets configurados, los PINs quedan vacíos
# y el acceso a SF6 queda bloqueado (fail-closed).
import streamlit as st


def _secret(section, key):
    try:
        return str(st.secrets[section][key])
    except Exception:
        return ""


USUARIO_MAESTRO = "SF"
PIN_MAESTRO = _secret("pins", "maestro")
PIN_ALMACEN = _secret("pins", "almacen")

# Rutas de Archivos
ARCHIVO_INVENTARIO = 'inventario_dap_guardado.csv'
ARCHIVO_VALES = 'vales_historial_guardado.json'
ARCHIVO_TERRITORIAL = 'DELEUTB2.csv'

# Catálogo Oficial Consolidado (10 Base + Sub-selecciones)
USUARIOS_OFICIALES = [
    "SF", "Director", "Jefe Mant", "Jefe Infra",
    "GuaDAP", "Almacen1", "Almacen2", "Ditto",
    "Especial", "Brigada"
]

# Constantes de Operación
BASE_COORDS = (19.291395219739588, -99.63555838631413)
LEYENDA_OFICIAL = "Este material es propiedad del Ayuntamiento de Toluca y se genera en la Dirección de Alumbrado Público"
