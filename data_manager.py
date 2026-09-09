import os
import pandas as pd
import json
import config

# --- Funciones para Inventario ---
def cargar_inventario():
    try:
        return pd.read_csv(config.ARCHIVO_INVENTARIO)
    except:
        return None

def guardar_inventario(df):
    df.to_csv(config.ARCHIVO_INVENTARIO, index=False)

# --- Funciones para Vales ---
def cargar_vales():
    try:
        with open(config.ARCHIVO_VALES, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def guardar_vales(lista_vales):
    with open(config.ARCHIVO_VALES, 'w', encoding='utf-8') as f:
        json.dump(lista_vales, f, ensure_ascii=False, indent=4)

def reiniciar_sistema():
    if os.path.exists(config.ARCHIVO_INVENTARIO):
        os.remove(config.ARCHIVO_INVENTARIO)
    if os.path.exists(config.ARCHIVO_VALES):
        os.remove(config.ARCHIVO_VALES)
