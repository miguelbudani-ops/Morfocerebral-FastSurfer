import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from pathlib import Path
import warnings
import re

# --- Funciones Auxiliares ---

def _normalizar_genero(genero_input: str) -> str:
    """
    Normaliza la entrada de género a 'M' o 'F'.

    Args:
        genero_input: String que representa el género (ej: "masculino", "fem", "F").

    Returns:
        'M' para masculino o 'F' para femenino.
        
    Raises:
        ValueError: Si la entrada no corresponde a ningún género conocido.
    """
    genero_lower = genero_input.lower()
    if genero_lower in ["m", "masc", "masculino"]:
        return 'M'
    elif genero_lower in ["f", "fem", "femenino"]:
        return 'F'
    else:
        raise ValueError(f"Género '{genero_input}' no reconocido. Use 'M' o 'F'.")

def _extraer_datos_sujeto(path_sujeto: Path, lista_estructuras: list) -> pd.DataFrame:
    """
    Extrae los datos de un sujeto específico para las estructuras de interés.

    Args:
        path_sujeto: Ruta al archivo .xlsx del sujeto.
        lista_estructuras: Lista de nombres de las estructuras a extraer.

    Returns:
        Un DataFrame de pandas con las columnas 'Estructura' y 'Valor'.
    """
    try:
        # La primera columna 'Measure:GrayVol' contiene los nombres de las estructuras.
        df_sujeto = pd.read_excel(path_sujeto, index_col=0)
    except FileNotFoundError:
        warnings.warn(f"El archivo del sujeto en '{path_sujeto}' no fue encontrado.")
        return pd.DataFrame({'Estructura': [], 'Valor': []})
        
    datos = []
    for estructura in lista_estructuras:
        if estructura not in df_sujeto.index:
            warnings.warn(
                f"Advertencia: La estructura '{estructura}' no se encontró en el archivo del sujeto "
                f"y será ignorada."
            )
            continue
            
        # Lógica condicional para extraer el valor correcto
        if 'Espesor cortical' in estructura:
            # Para espesor, usamos la columna 'Volumen mm3 (sujeto)' (que es el valor en mm)
            valor = df_sujeto.lfont_paramsoc[estructura, 'Volumen mm3 (sujeto)']
        else:
            # Para volumen, usamos el valor relativo ya calculado en 'Volrel% (sujeto)'
            valor = df_sujeto.loc[estructura, 'Volrel% (sujeto)']
        
        datos.append({'Estructura': estructura, 'Valor': valor})
        
    return pd.DataFrame(datos)

# --- Función Principal ---

def generar_graficos_volumen_edad(
    genero_paciente: str,
    edad_paciente: int,
    path_sujeto: str,
    path_poblacion_dir: str,
    path_salida: str
):
    """
    Genera y guarda gráficos que comparan el volumen cerebral de un sujeto
    con datos normativos de una población, mostrando la variación con la edad.

    Args:
        genero_paciente (str): Género del paciente ('M', 'F', 'masculino', etc.).
        edad_paciente (int): Edad del paciente en años.
        path_sujeto (str): Ruta al archivo .xlsx con los datos del paciente.
        path_poblacion_dir (str): Ruta al DIRECTORIO que contiene los archivos de población 
                                 (ej: 'F_vol_vs_tiempo.xlsx').
        path_salida (str): Ruta a la carpeta donde se guardarán los gráficos .png.
    """
    # 1. Preparación y validación de entradas
    try:
        letra_genero = _normalizar_genero(genero_paciente)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Definimos la lista de estructuras a graficar.
    estructuras_a_graficar = [
                'Hipocampo', 'Ventrículos Laterales','Volumen cerebral total','Sustancia gris total','Sustancia blanca total','Sustancia gris corteza izquierda','Sustancia gris corteza derecha',
    ]

    # Convertir paths de string a objetos Path
    p_poblacion_dir = Path(path_poblacion_dir)
    p_sujeto = Path(path_sujeto)
    p_salida = Path(path_salida)

    p_salida.mkdir(parents=True, exist_ok=True)

    # 2. Carga y procesamiento de datos de la POBLACIÓN
    nombre_archivo_poblacion = f"{letra_genero}_vol_vs_tiempo.xlsx"
    path_archivo_poblacion = p_poblacion_dir / nombre_archivo_poblacion
    
    try:
        df_poblacion = pd.read_excel(path_archivo_poblacion, index_col=0)
    except FileNotFoundError:
        warnings.warn(f"Archivo de población no encontrado en '{path_archivo_poblacion}'. No se generarán gráficos.")
        return

    # --- LÍNEA CORREGIDA ---
    # Extraer edades usando SOLO los últimos 2 dígitos del nombre de la columna.
    try:
        edades = [int(re.search(r'\d{2}$', col).group()) for col in df_poblacion.columns]
        df_poblacion.columns = edades
    except AttributeError:
        warnings.warn("No se pudo extraer la edad de los nombres de columna. Asegúrese de que terminan en dos dígitos.")
        return

    # Normalización de los volúmenes
    df_relativo = pd.DataFrame(index=df_poblacion.index, columns=df_poblacion.columns)
    vol_intracraneal_total = df_poblacion.loc['Volumen total intracraneal']

    for estructura in df_poblacion.index:
        if 'Espesor cortical' in estructura:
            df_relativo.loc[estructura] = df_poblacion.loc[estructura]
        elif estructura == 'Volumen total intracraneal':
            continue
        else:
            df_relativo.loc[estructura] = (df_poblacion.loc[estructura] / vol_intracraneal_total) * 100

    # 3. Carga de datos del SUJETO
    df_datos_sujeto = _extraer_datos_sujeto(p_sujeto, estructuras_a_graficar)
    if df_datos_sujeto.empty:
        print("No se pudieron extraer los datos del sujeto. Finalizando.")
        return

    # 4. Generación de gráficos (un gráfico por estructura)
    print("Iniciando generación de gráficos...")
    for estructura in estructuras_a_graficar:
        if estructura not in df_relativo.index or estructura not in df_datos_sujeto['Estructura'].values:
            warnings.warn(f"Omitiendo gráfico para '{estructura}' por falta de datos en alguno de los archivos.")
            continue

        # --- PREPARACIÓN DE DATOS (SIN CAMBIOS) ---
        y_poblacion = df_relativo.loc[estructura].dropna().astype(float)
        x_poblacion = y_poblacion.index.astype(int)
        
        y_poblacion = y_poblacion.groupby(y_poblacion.index).mean()
        x_poblacion = y_poblacion.index
        
        idx_sorted = np.argsort(x_poblacion)
        x_poblacion = np.array(x_poblacion)[idx_sorted]
        y_poblacion = y_poblacion.iloc[idx_sorted]
        
        valor_sujeto = df_datos_sujeto.loc[df_datos_sujeto['Estructura'] == estructura, 'Valor'].iloc[0]
        
        # --- LÓGICA DE SUAVIZADO REEMPLAZADA POR REGRESIÓN ---

        # Grado del polinomio. 2 = parábola (recomendado), 1 = línea recta.
        degree = 1
        
        # Ajustar el polinomio a los datos de la población (x=edad, y=volumen)
        coeffs = np.polyfit(x_poblacion, y_poblacion, degree)
        
        # Crear una función a partir de los coeficientes del polinomio
        p = np.poly1d(coeffs)
        
        # Generar los puntos para la curva suave usando un rango de edades
        x_smooth = np.linspace(x_poblacion.min(), x_poblacion.max(), 300)
        y_smooth = p(x_smooth)

        # Los límites de confianza ahora se calculan sobre la curva de regresión
        # Esto requiere un enfoque estadístico más avanzado (bandas de predicción).
        # Por simplicidad visual, mantenemos el rolling_std sobre la curva original
        # para dar una idea de la dispersión, aunque no sea una banda de predicción formal.
        rolling_std = y_poblacion.rolling(window=5, center=True, min_periods=1).std()
        std_mean = rolling_std.mean() # Usamos una desviación estándar promedio para la banda
        
        upper_bound = y_smooth + (3 * std_mean)
        lower_bound = y_smooth - (3 * std_mean)

        # --- FIN DE LA SECCIÓN DE REGRESIÓN ---

        # --- SECCIÓN DE GRÁFICO (CON AJUSTES MENORES) ---
        fig, ax = plt.subplots(figsize=(8.8, 6))
        ax.set_facecolor("#ffffff")

        # Ahora usamos x_smooth para los límites para que coincidan con la curva
        ax.fill_between(x_smooth, lower_bound, upper_bound, color="#F3F3F399", alpha=0.7)
        ax.plot(x_smooth, lower_bound, color='orangered', linestyle='--', linewidth=1.5)
        ax.plot(x_smooth, upper_bound, color='orangered', linestyle='--', linewidth=1.5)
        
        ax.plot(x_smooth, y_smooth, color="#9E9E9E", linewidth=4, label='Tendencia Poblacional')
        ax.scatter(edad_paciente, valor_sujeto, color="#9e9e9e", s=130, zorder=5, edgecolor='gray', linewidth=1.5, label=f'Sujeto')

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

        font_params = {'fontweight': 'bold', 'fontsize': 14, 'fontname': 'sans-serif','color':'gray'}
        ax.set_xlabel('Edad', **font_params)
        
        y_label = 'Volumen (%VIC)' if 'Espesor cortical' not in estructura else 'Espesor (mm)'
        ax.set_ylabel(y_label, **font_params)

        ax.tick_params(axis='both', which='major', labelsize=12, labelcolor='#333333')
        nombre_archivo_salida = f"{estructura.replace(' ', '_').replace('(', '').replace(')', '')}_vs_tiempo.png"
        ruta_guardado = p_salida / nombre_archivo_salida
        fig.savefig(ruta_guardado, dpi=300, bbox_inches='tight')
        plt.close(fig)

        print(f"Gráfico para '{estructura}' guardado en '{ruta_guardado}'")

    print("\nProceso completado.")


# --- EJEMPLO DE USO ---
if __name__ == '__main__':
    # DEBES MODIFICAR ESTAS RUTAS ANTES DE EJECUTAR
    
    # Ruta al directorio que contiene los archivos 'F_vol_vs_tiempo.xlsx' y 'M_vol_vs_tiempo.xlsx'
    directorio_poblacion = "/home/usuario/Bibliografia/pipeline_v2/recursos/morfo_cerebral/Temporales"       
    
    # Ruta al archivo .xlsx del paciente/sujeto
    archivo_sujeto = "/home/usuario/Descargas/DIAZ/dicom/Fastsurfer/stats/Especificos.xlsx"
    # Carpeta donde se guardarán las imágenes generadas
    carpeta_salida = "/home/usuario/Descargas/DIAZ/dicom/Fastsurfer/stats/graficos_temporales"

    # Datos del paciente
    genero = "fem"  # Puede ser "F", "fem", "femenino"
    edad = 55            # Edad en años

    # Llamada a la función principal
    generar_graficos_volumen_edad(
        genero_paciente=genero,
        edad_paciente=edad,
        path_sujeto=archivo_sujeto,
        path_poblacion_dir=directorio_poblacion,
        path_salida=carpeta_salida
    )
