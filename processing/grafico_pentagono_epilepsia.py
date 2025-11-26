import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import os
import textwrap # <-- 1. Importar la librería necesaria


def _cargar_especificos_excel(path_excel: str | Path) -> pd.DataFrame:
    df = pd.read_excel(path_excel)
    esperadas = {
        "Measure:GrayVol","Volumen mm3 (sujeto)","Volrel% (sujeto)","Mediana","IC_95%_Bajo",
        "IC_95%_Alto","IC_99%_Bajo","IC_99%_Alto","Percentil (sujeto)",
        "Flag","Z_sujeto","Dentro_de_Umbral_±3.5"
    }

    faltan = esperadas.difference(df.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en {path_excel}: {faltan}")
    return df

def extraer_mediana_volumen_df(df, medidas):
    registros = []
    for medida in medidas:
        fila = df[df['Measure:GrayVol'] == medida]
        if not fila.empty:
            registros.append({
                'Measure': medida,
                'Mediana': fila.iloc[0]['Mediana'] / 1000,          # cm³
                'Volumen cm3': fila.iloc[0]['Volumen mm3 (sujeto)'] / 1000   # cm³
            })
    return pd.DataFrame(registros)

def dibujar_pentagono(df, archivo_salida):

    df['Pct_rel'] = df['Volumen cm3'] / df['Mediana'] * 100
    
    labels        = df['Measure'].tolist()
    vals_paciente = np.append(df['Pct_rel'].values, df['Pct_rel'].values[0])

    n = len(labels)
    angulos = np.linspace(0, 2*np.pi, n, endpoint=False)
    angulos = np.append(angulos, angulos[0])

    # Paleta (sin cambios)
    C_MEDIANA   = "#ff8fd4"
    C_U25       = "#6fa8dc"
    C_U50       = "#e06666"
    C_PAC_FILL  = "#f7f7f7"     
    C_PAC_EDGE  = "#9B9B9B"
    C_FRAME     = "#787878"
    C_GRID      = "#d0d0d0"

    # Radio exterior (sin cambios)
    r_outer = float(np.ceil(max(120.0, float(vals_paciente.max())*1.20)/5)*5)
    outer = np.append(np.full(n, r_outer), r_outer)

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1)
    ax.set_ylim(0, r_outer)
    ax.grid(False); ax.set_xticks([]); ax.set_yticks([])
    ax.spines['polar'].set_visible(False)
    ax.set_facecolor('white')
    
    for angle in angulos[:-1]:
        ax.plot([angle, angle], [0, r_outer], color=C_GRID, linestyle='dotted', linewidth=1, zorder=0)

    ax.plot(angulos, outer, color=C_FRAME, linewidth=2.2, zorder=1)
    ax.fill(angulos, outer, facecolor="#fff9e6", alpha=0.1, zorder=0)

    # Mediana (100%) (sin cambios)
    med = np.append(np.full(n, 100.0), 100.0)
    ax.plot(angulos, med, color=C_MEDIANA, linewidth=2.8, label='Mediana', zorder=3)

    # Paciente (más claro) (sin cambios)
    ax.plot(angulos, vals_paciente, color=C_PAC_EDGE, linewidth=2, zorder=4)
    ax.fill(angulos, vals_paciente, color=C_PAC_FILL, alpha=0.6, label='Paciente', zorder=3)
   
    # Umbrales (sin cambios)
    for pct, col, lbl in [(25, C_U25, 'Umbral 25%'), (50, C_U50, 'Umbral 50%')]:
        arr = np.append(np.full(n, pct), pct)
        ax.plot(angulos, arr, color=col, linestyle=(0, (3, 3)), linewidth=1.5, label=lbl, zorder=5)

    # --- INICIO DE LA MODIFICACIÓN ---

    # 2. Aumentamos ligeramente la distancia para dar espacio a las dos líneas
    etiqueta_r = r_outer * 1.1 

    for label, theta in zip(labels, angulos[:-1]):
        # 3. Dividimos la etiqueta en múltiples líneas si es muy larga
        wrapped_label = textwrap.fill(label, width=20, break_long_words=False)

        phi = np.pi/2 - theta
        ha = 'center' if np.isclose(np.cos(phi), 0, atol=1e-2) else ('right' if np.cos(phi) < 0 else 'left')
        va = 'center' # Usamos 'center' para un mejor alineamiento vertical del texto de dos líneas
        
        # Usamos la etiqueta dividida (wrapped_label) para dibujar el texto
        ax.text(theta, etiqueta_r, wrapped_label, ha=ha, va=va, fontsize=13, color="gray", fontweight='bold')
    
    # --- FIN DE LA MODIFICACIÓN ---

    # Leyenda (sin cambios)
    legend_elems = [
        Patch(facecolor=C_PAC_FILL, edgecolor=C_PAC_EDGE, label='Paciente'),
        Line2D([0], [0], color=C_U50, lw=3, linestyle=(0, (3, 3)), label='Umbral 50%'),
        Line2D([0], [0], color=C_U25, lw=3, linestyle=(0, (3, 3)), label='Umbral 25%'),
        Line2D([0], [0], color=C_MEDIANA, lw=2.8, label='Mediana'),
    ]
    ax.legend(handles=legend_elems, loc='upper right', bbox_to_anchor=(1.35, 1.10), frameon=False)

    archivo_salida = Path(archivo_salida); archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(archivo_salida), dpi=300, bbox_inches='tight')
    plt.close(fig)

def poligono_epilepsia(stats_folder):
    excel_especificos=os.path.join(stats_folder,'Especificos.xlsx')
    path = Path(excel_especificos)
    df0  = _cargar_especificos_excel(path)
    df1  = extraer_mediana_volumen_df(
               df0, ["Sustancia gris corteza izquierda","Sustancia blanca total", "Sustancia gris profunda", "Sustancia gris corteza derecha"]
           )
    out  = Path(stats_folder) / "pentagono_epilepsia.png"
    dibujar_pentagono(df1, out)