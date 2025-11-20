import pandas as pd
from pathlib import Path

def agregar_volumen_relativo(path_csv, nombre_salida="con_volumen_relativo.csv"):
    """
    Agrega una columna 'volumen_relativo' al CSV, calculando el porcentaje de cada estructura
    respecto al volumen intracraneal total (eTIV).

    Parámetros:
    ----------
    path_csv : str or Path
        Ruta al archivo CSV original con las columnas: seccion, id_corto, descripcion, valor, unidad.
    nombre_salida : str
        Nombre del archivo de salida con la columna adicional.

    Salida:
    ------
    Un archivo CSV con la columna 'volumen_relativo' expresada en porcentaje.
    """
    path_csv = Path(path_csv)
    df = pd.read_csv(path_csv)

    # Buscar el valor de eTIV
    etiv_fila = df[df["id_corto"] == "eTIV"]
    if etiv_fila.empty:
        raise ValueError("❌ No se encontró la fila con id_corto == 'eTIV'")

    etiv_valor = etiv_fila["valor"].values[0]

    # Calcular volumen relativo
    df["volumen_relativo"] = (df["valor"] / etiv_valor) * 100

    # Guardar el nuevo CSV
    salida = path_csv.parent / nombre_salida
    df.to_csv(salida, index=False, encoding="utf-8")
    print(f"✅ Archivo generado con volumen relativo: {salida}")
agregar_volumen_relativo("/home/mbudani/results/procesamiento/volbrain/fastsurfer/csv_promedio.csv")
agregar_volumen_relativo("/home/mbudani/results/procesamiento/volbrain/FS/csv_promedio.csv")
agregar_volumen_relativo("/home/mbudani/results/procesamiento/volbrain/synthseg/csv_promedio.csv")