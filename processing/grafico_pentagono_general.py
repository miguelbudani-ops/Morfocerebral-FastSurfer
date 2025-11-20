import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import os
import textwrap  # Import needed for label wrapping

def _cargar_especificos_excel(path_excel: str | Path) -> pd.DataFrame:
    df = pd.read_excel(path_excel)
    esperadas = {
        "Measure:GrayVol", "Volumen mm3 (sujeto)", "Volrel% (sujeto)", "Mediana", "IC_95%_Bajo",
        "IC_95%_Alto", "IC_99%_Bajo", "IC_99%_Alto", "Percentil (sujeto)",
        "Flag", "Z_sujeto", "Dentro_de_Umbral_±3.5"
    }
    faltan = esperadas.difference(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en {path_excel}: {faltan}")
    return df

def extraer_mediana_volumen_df(df1, medidas,path_stats):
    """
    Extrae la mediana y el valor del sujeto para una lista de medidas.
    Maneja de forma inteligente tanto volúmenes como espesores.
    """

    archivo_xlsx = os.path.join(path_stats, 'volumetria.xlsx')
    df = pd.read_excel(archivo_xlsx, sheet_name='Volumenes')

   

    Volumenes_Sust_Blanca = [
        'Sustancia blanca cerebral derecha',
        'Sustancia blanca cerebral izquierda'
    ]

    datos_filtrados = df[df['Regiones_ESP'].isin(Volumenes_Sust_Blanca)]
    registros = []

    fila = df[df['Regiones_ESP'] == 'Sustancia blanca cerebral derecha']
    valor_sujeto = fila.iloc[0]['Volumen_%VIT']
    registros.append({
        'Measure': 'Sustancia blanca cerebral derecha',
        'Mediana': fila.iloc[0]['Mediana'],
        'Valor Sujeto': valor_sujeto  # Columna renombrada para mayor claridad
    })

    fila = df[df['Regiones_ESP'] == 'Sustancia blanca cerebral izquierda']
    valor_sujeto = fila.iloc[0]['Volumen_%VIT']
    registros.append({
        'Measure': 'Sustancia blanca cerebral izquierda',
        'Mediana': fila.iloc[0]['Mediana'],
        'Valor Sujeto': valor_sujeto  # Columna renombrada para mayor claridad
    })

    df_vol = pd.DataFrame(registros)

    registros = []

    # 1. Limpiamos los nombres de las estructuras en el DataFrame de entrada (df1)
    df1_stripped = df1.copy()
    df1_stripped['Measure:GrayVol'] = df1_stripped['Measure:GrayVol'].str.strip()

    # 2. Convertimos las columnas de valores a tipo string, reemplazamos comas por puntos, y convertimos a número
    #    Esto soluciona el error de "15,51" vs "15.51"
    cols_a_convertir = ['Volumen mm3 (sujeto)', 'Volrel% (sujeto)', 'Mediana']
    for col in cols_a_convertir:
        if col in df1_stripped.columns:
            df1_stripped[col] = pd.to_numeric(
                df1_stripped[col].astype(str).str.replace(',', '.'), 
                errors='coerce'
            )

    for medida in medidas:
        # Usamos .str.strip() para evitar problemas con espacios en blanco invisibles
        # ✅ CORRECCIÓN: Usar df1_stripped, que tiene los números ya convertidos
        fila = df1_stripped[df1_stripped['Measure:GrayVol'] == medida.strip()]

        if not fila.empty:
            valor_sujeto = 0
            
            if 'Espesor cortical' in medida:
                #Apuntamos a 'Volumen mm3 (sujeto)' que contiene el espesor en mm
                valor_sujeto = fila.iloc[0]['Volumen mm3 (sujeto)']
                
                registros.append({
                'Measure': medida,
                'Mediana': fila.iloc[0]['Mediana'],
                'Valor Sujeto': valor_sujeto
            })
            else:
                
                valor_sujeto = fila.iloc[0]['Volrel% (sujeto)']

                registros.append({
                    'Measure': medida,
                    'Mediana': fila.iloc[0]['Volrel%'],
                    'Valor Sujeto': valor_sujeto
                })

    df_registros = pd.DataFrame(registros)
    return pd.concat([df_registros, df_vol], ignore_index=True)

def dibujar_pentagono(df, archivo_salida):
    df['Pct_rel'] = df['Valor Sujeto'] / df['Mediana'] * 100

    labels = df['Measure'].tolist()
    vals_paciente = np.append(df['Pct_rel'].values, df['Pct_rel'].values[0])

    n = len(labels)
    angulos = np.linspace(0, 2 * np.pi, n, endpoint=False)
    angulos = np.append(angulos, angulos[0])

    # Paleta
    C_MEDIANA = "#f1c232"  # amarillo (corregido de 'azul')
    C_U25 = "#6fa8dc"  # celeste
    C_U50 = "#e06666"  # rojo suave
    C_PAC_FILL = "#cff1ff"
    C_PAC_EDGE = "#3275f1"
    C_FRAME = "#787878"
    C_GRID = "#d0d0d0"

    # Radio exterior
    # Manejo de posible error si vals_paciente está vacío o tiene NaN
    valid_vals = vals_paciente[np.isfinite(vals_paciente)]
    if valid_vals.size == 0:
        max_val = 120.0
    else:
        max_val = valid_vals.max()
        
    r_outer = float(np.ceil(max(120.0, max_val * 1.20) / 5) * 5)
    outer = np.append(np.full(n, r_outer), r_outer)

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, r_outer)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['polar'].set_visible(False)
    ax.set_facecolor('white')
    
    for angle in angulos[:-1]:
        ax.plot([angle, angle], [0, r_outer], color=C_GRID, linestyle='dotted', linewidth=1, zorder=0)

    ax.plot(angulos, outer, color=C_FRAME, linewidth=2.2, zorder=1)
    ax.fill(angulos, outer, facecolor="#fff9e6", alpha=0.1, zorder=0)

    # Mediana (100%)
    med = np.append(np.full(n, 100.0), 100.0)
    ax.plot(angulos, med, color=C_MEDIANA, linewidth=2.8, label='Mediana', zorder=3)

    # Paciente (más claro)
    ax.plot(angulos, vals_paciente, color=C_PAC_EDGE, linewidth=2, zorder=4)
    ax.fill(angulos, vals_paciente, color=C_PAC_FILL, alpha=0.6, label='Paciente', zorder=3)

    # Umbrales: 25% y 50% con trazos **más juntos** y más gruesos
    for pct, col, lbl in [(25, C_U25, 'Umbral 25%'), (50, C_U50, 'Umbral 50%')]:
        arr = np.append(np.full(n, pct), pct)
        ax.plot(angulos, arr, color=col, linestyle=(0, (3, 3)), linewidth=1.5, label=lbl, zorder=5)

    # --- INICIO BLOQUE ETIQUETAS CORREGIDO ---
    etiqueta_r = r_outer * 1.1  # Aumentamos distancia para texto en 2 líneas

    for label, theta in zip(labels, angulos[:-1]):
        # Dividimos la etiqueta en múltiples líneas
        wrapped_label = textwrap.fill(label, width=20, break_long_words=False)

        phi = np.pi / 2 - theta
        ha = 'center' if np.isclose(np.cos(phi), 0, atol=1e-2) else ('right' if np.cos(phi) < 0 else 'left')
        va = 'center'  # 'center' funciona mejor para texto de múltiples líneas

        ax.text(theta, etiqueta_r, wrapped_label, ha=ha, va=va, fontsize=13, color="gray", fontweight='bold')
    # --- FIN BLOQUE ETIQUETAS CORREGIDO ---

    # Leyenda
    legend_elems = [
        Patch(facecolor=C_PAC_FILL, edgecolor=C_PAC_EDGE, label='Paciente'),
        Line2D([0], [0], color=C_U50, lw=3, linestyle=(0, (3, 3)), label='Umbral 50%'),
        Line2D([0], [0], color=C_U25, lw=3, linestyle=(0, (3, 3)), label='Umbral 25%'),
        Line2D([0], [0], color=C_MEDIANA, lw=2.8, label='Mediana'),
    ]
    ax.legend(handles=legend_elems, loc='upper right', bbox_to_anchor=(1.35, 1.10), frameon=False)

    archivo_salida = Path(archivo_salida)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(archivo_salida), dpi=300, bbox_inches='tight')
    plt.close(fig)

def poligono_general(stats_folder:str):
    
    excel_especificos=os.path.join(stats_folder,'Especificos.xlsx')
    excel_especificos=Path(excel_especificos)
    df0 = _cargar_especificos_excel(excel_especificos)
    df1 = extraer_mediana_volumen_df(
        df0, ["Espesor cortical derecho (mm)", "Espesor cortical izquierdo (mm)", "Sustancia gris corteza derecha", "Sustancia gris corteza izquierda"]
    ,stats_folder)
    out = os.path.join(stats_folder,"pentagono_volumenes_general.png")
    out=Path(out)
    dibujar_pentagono(df1, out)