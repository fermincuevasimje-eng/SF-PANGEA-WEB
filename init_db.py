import pandas as pd
import data_manager

# Creamos una estructura básica para que el archivo nazca bien
df = pd.DataFrame(columns=['ID', 'Material', 'Stock', 'Min', 'Unidad'])

# Lo guardamos con tu encargado de almacén
data_manager.guardar_inventario(df)

print("¡Listo! El archivo inventario_dap_guardado.csv ya debería existir.")
