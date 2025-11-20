import pandas as pd
from pathlib import Path

def generar_csv_promedio(dir_csvs, nombre_salida="promedio.csv"):
    """
    Genera un archivo CSV con el promedio de la columna 'valor' o DICE o hd95 segun elijas a partir de múltiples CSVs
    con estructura idéntica y filas alineadas.

    Parámetros:
    ----------
    dir_csvs : str or Path
        Directorio que contiene los archivos CSV por sujeto.
    nombre_salida : str
        Nombre del archivo de salida con los valores promedio.

    Salida:
    ------
    Un archivo CSV en el mismo directorio con los valores promedio por fila.
    """
    dir_csvs = Path(dir_csvs)
    archivos = sorted(dir_csvs.glob("*.csv"))

    
    excluir = {"hd95_combined.csv"}
    archivos = sorted([
        archivo for archivo in dir_csvs.glob("*.csv")
        if archivo.name not in excluir
    ])

    if not archivos:
        raise FileNotFoundError("❌ No se encontraron archivos CSV en el directorio")

    # Leer todos los CSVs en una lista de DataFrames
    dfs = [pd.read_csv(archivo) for archivo in archivos]

    # Validar que todos tengan la misma estructura
    columnas_base = dfs[0].columns.tolist()
    for i, df in enumerate(dfs):
        if df.columns.tolist() != columnas_base:
            raise ValueError(f"❌ El archivo {archivos[i].name} tiene columnas distintas")

    # Concatenar los valores de 'valor' en un DataFrame auxiliar
    valores = pd.concat([df["hd95_mm"] for df in dfs], axis=1)
    promedio_valores = valores.mean(axis=1)

    # Crear nuevo DataFrame con columnas fijas y valores promedio
    df_promedio = dfs[0].copy()
    df_promedio["hd95_mm"] = promedio_valores

    # Guardar el resultado
    salida = dir_csvs / nombre_salida
    df_promedio.to_csv(salida, index=False, encoding="utf-8")
    print(f"✅ CSV promedio generado en: {salida}")

#generar_csv_promedio("/home/mbudani/results/procesamiento/HD95/clinical", nombre_salida="csv_promedio.csv")
#generar_csv_promedio("/home/mbudani/results/procesamiento/HD95/clinical/hdb5_cortex", nombre_salida="csv_promedio.csv")
#generar_csv_promedio("/home/mbudani/results/procesamiento/HD95/clinical/hdb5_subcortex", nombre_salida="csv_promedio.csv")
#generar_csv_promedio("/home/mbudani/results/procesamiento/HD95/fastsurfer", nombre_salida="csv_promedio.csv")
#generar_csv_promedio("/home/mbudani/results/procesamiento/HD95/fastsurfer/hdb5_cortex", nombre_salida="csv_promedio.csv")
#generar_csv_promedio("/home/mbudani/results/procesamiento/HD95/fastsurfer/hdb5_subcortex", nombre_salida="csv_promedio.csv")
#generar_csv_promedio("/home/mbudani/results/procesamiento/HD95/synthseg", nombre_salida="csv_promedio.csv")
#generar_csv_promedio("/home/mbudani/results/procesamiento/HD95/synthseg/hdb5_subcortex", nombre_salida="csv_promedio.csv")
generar_csv_promedio("/home/mbudani/results/fastsurfer_array_results_2021/HD95", nombre_salida="csv_fast_promedio.csv")