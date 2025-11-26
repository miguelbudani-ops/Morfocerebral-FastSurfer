import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import os
import textwrap

from processing.specific_analysis import _warn  # Import needed for label wrapping


def _read_transposed_series(path: str) -> pd.Series:
    """
    Lee un archivo de tabla transpuesta (ROI en filas, sujeto en una columna numérica).
    Devuelve una Serie: index = ROI, values = float del sujeto.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe archivo: {path}")
    df = pd.read_csv(path, sep=r"\s+", comment="#")
    idx = df.columns[0]
    # Tomar la primera columna numérica (sujeto)
    numcols = [c for c in df.columns[1:] if pd.api.types.is_numeric_dtype(df[c])]
    if not numcols:
        # intentar convertir forzadamente
        for c in df.columns[1:]:
            try:
                df[c] = pd.to_numeric(df[c], errors="coerce")
                if df[c].notna().any():
                    numcols = [c]
                    break
            except Exception:
                pass
    if not numcols:
        raise ValueError(f"No se encontró columna numérica de sujeto en {path}")
    return df.set_index(idx)[numcols[0]].astype(float)

def seleccionar_base_control_espesores(edad, genero):
    """
    Selecciona la base de datos control de espesores según edad y género.
    """
    base_dir = "/home/usuario/Bibliografia/pipeline_v2/recursos/morfo_cerebral/espesor_cortical"
    if edad <= 18:
        grupo = "18_29"
    elif edad <= 29:
        grupo = "18_29"
    elif edad <= 44:
        grupo = "30_44"
    elif edad <= 60:
        grupo = "45_60"
    else:
        grupo = "45_60"

    genero_norm = genero.strip().lower()
    if genero_norm in {"f", "femenino", "female"}:
        genero = "femenino"
    elif genero_norm in {"m", "masculino", "male"}:
        genero = "masculino"
    else:
        raise ValueError(f"Género no reconocido: {genero!r}")
    
    file_path_estadisticos_control_lh = os.path.join(base_dir, f"grupo_{grupo}_{genero}_aparc_lh_stats_thickness_Z_Scores_Robustos.xlsx")
    file_path_estadisticos_control_rh = os.path.join(base_dir, f"grupo_{grupo}_{genero}_aparc_rh_stats_thickness_Z_Scores_Robustos.xlsx")

    # Verificar existencia de los archivos
    if not os.path.exists(file_path_estadisticos_control_lh) or not os.path.exists(file_path_estadisticos_control_rh):
        raise RuntimeError(f"No se encontraron los archivos de base de control en: {base_dir}")

    return file_path_estadisticos_control_lh, file_path_estadisticos_control_rh




def extraer_mediana_volumen_df(stats_folder,edad, genero):
    """
    Extrae la mediana y el valor del sujeto para una lista de medidas.
    Maneja de forma inteligente tanto volúmenes como espesores.
    """

    # Obtener archivos de espesores del paciente
    file_path_paciente_lh = os.path.join(stats_folder, "lh_aparc.DKTatlas.mapped_thickness_stats.txt")
    file_path_paciente_rh = os.path.join(stats_folder, "rh_aparc.DKTatlas.mapped_thickness_stats.txt")

    # Seleccionar base de datos control
    file_path_estadisticos_control_lh, file_path_estadisticos_control_rh = seleccionar_base_control_espesores(edad, genero)

    # Leer archivos del paciente y del grupo control
    #df_paciente_lh = pd.read_csv(file_path_paciente_lh, sep='\t', index_col='lh.aparc.DKTatlas.mapped.thickness')
    #df_paciente_rh = pd.read_csv(file_path_paciente_rh, sep='\t', index_col='rh.aparc.DKTatlas.mapped.thickness')

    df_paciente_lh = _read_transposed_series(file_path_paciente_lh)  # e.g., 'lh_cuneus_volume'
    df_paciente_rh = _read_transposed_series(file_path_paciente_rh)  # e.g., 'rh_cuneus_volume'

    df_control_lh = pd.read_excel(file_path_estadisticos_control_lh, index_col='Measure:thickness', engine='openpyxl')
    df_control_rh = pd.read_excel(file_path_estadisticos_control_rh, index_col='Measure:thickness', engine='openpyxl')




    _LOBES: Dict[str, List[str]] = {
    'Frontal': [
        'caudalanteriorcingulate','caudalmiddlefrontal','lateralorbitofrontal',
        'medialorbitofrontal','parsopercularis','parsorbitalis','parstriangularis',
        'precentral','superiorfrontal','rostralanteriorcingulate','rostralmiddlefrontal','paracentral'
    ],
    'Parietal': ['superiorparietal','inferiorparietal','supramarginal','postcentral','precuneus'],
    'Temporal': ['superiortemporal','middletemporal','inferiortemporal','fusiform','transversetemporal','parahippocampal'],
    'Occipital': ['lateraloccipital','cuneus','pericalcarine','lingual'],
    }

    def _get_from_series(source: pd.Series | pd.DataFrame, hemi: str, roi: str) -> float:
        """
        Recupera el valor del ROI para el hemisferio indicado desde una Serie (paciente)
        o desde un DataFrame (estadísticos), normalizando los patrones de nombres.
        """
        patterns = (
            f"{hemi}_{roi}_thickness",
            f"{hemi}.{roi}.thickness",
            f"{hemi}-{roi}-thickness",
        )

        if isinstance(source, pd.DataFrame):
            for pat in patterns:
                if pat in source.index:
                    if "Mediana" not in source.columns:
                        raise KeyError("La columna 'Mediana' no está presente en la base de control.")
                    return float(source.at[pat, "Mediana"])
            if roi in source.index:
                if "Mediana" not in source.columns:
                    raise KeyError("La columna 'Mediana' no está presente en la base de control.")
                return float(source.at[roi, "Mediana"])
        else:
            for pat in patterns:
                if pat in source.index:
                    return float(source[pat])
            if roi in source.index:
                return float(source[roi])

        _warn(f"ROI ausente para lóbulo: {hemi} {roi}")
        return float("nan")

    lobes_thickness_mm, lobes_thickness_mean_mm = {}, {}
    for lobe, rois in _LOBES.items():
        lh = np.nansum([_get_from_series(df_paciente_lh , "lh", r) for r in rois])/len(rois)
        rh = np.nansum([_get_from_series(df_paciente_rh, "rh", r) for r in rois])/len(rois)
        lobes_thickness_mm[lobe] = float(lh + rh)/2
        lh_control = np.nansum([_get_from_series(df_control_lh , "lh", r) for r in rois])/len(rois)
        rh_control = np.nansum([_get_from_series(df_control_rh, "rh", r) for r in rois])/len(rois)
        lobes_thickness_mean_mm[lobe] = float(lh_control + rh_control)/2
    print("\n➤ Espesores corticales del sujeto (mm):")
    for lobe in _LOBES.keys():
        print(f"{lobe}: {lobes_thickness_mm[lobe]:.4f} mm (Mediana Control: {lobes_thickness_mean_mm[lobe]:.4f} mm)")


    registros = []
    for lobe in _LOBES.keys():
        print(f"{lobe}: {lobes_thickness_mm[lobe]:.4f} mm (Mediana Control: {lobes_thickness_mean_mm[lobe]:.4f} mm)")
        valor_sujeto = lobes_thickness_mm[lobe]
        mediana_control = lobes_thickness_mean_mm[lobe]
        print(f"{lobe}: {valor_sujeto:.4f} mm (Mediana Control: {mediana_control:.4f} mm)")
        registros.append(
            {
                "Measure": f"Lóbulo {lobe.lower()}",
                "Valor Sujeto": valor_sujeto,
                "Mediana": mediana_control,
            }
        )

    return pd.DataFrame(registros)

def dibujar_pentagono(df, archivo_salida):
    df['Pct_rel'] = df['Valor Sujeto'] / df['Mediana'] * 100

    labels = df['Measure'].tolist()
    vals_paciente = np.append(df['Pct_rel'].values, df['Pct_rel'].values[0])

    n = len(labels)
    angulos = np.linspace(0, 2 * np.pi, n, endpoint=False)
    angulos = np.append(angulos, angulos[0])

    # Paleta
    C_MEDIANA = "#328bf1"  # amarillo (corregido de 'azul')
    C_U25 = "#6fa8dc"  # celeste
    C_U50 = "#e06666"  # rojo suave
    C_PAC_FILL = "#f0ddff"
    C_PAC_EDGE = "#bd4bff"
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
    ax.fill(angulos, outer, facecolor="#fff9e6", alpha=0.25, zorder=0)

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
        wrapped_label = textwrap.fill(label, width=15, break_long_words=False)

        phi = np.pi / 2 - theta
        ha = 'center' if np.isclose(np.cos(phi), 0, atol=1e-2) else ('right' if np.cos(phi) < 0 else 'left')
        va = 'center'  # 'center' funciona mejor para texto de múltiples líneas

        ax.text(theta, etiqueta_r, wrapped_label, ha=ha, va=va, fontsize=13, color='gray', fontweight='bold')
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

def pentagono_espesores(stats_folder,edad,genero):
    df_lobulos = extraer_mediana_volumen_df(stats_folder, edad, genero)
    stats_folder=Path(stats_folder)
    salida = stats_folder /"pentagono_espesores_lobulos.png"
    dibujar_pentagono(df_lobulos, salida)