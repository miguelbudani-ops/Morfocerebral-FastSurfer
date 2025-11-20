from pathlib import Path
import logging
from typing import Iterable, Optional, Tuple, Dict

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np 

# ============================================================
# Logging
# ============================================================
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("scatter-vs-fs")


# ============================================================
# Lectura y preparación de CSV
# ============================================================
REQUIRED_COLS = {"seccion", "id_corto", "descripcion", "valor", "unidad"}

# Añade esto al top si no está:
import numpy as np
import logging
logger = logging.getLogger("scatter-vs-fs")

def _compute_trend(x_pos: np.ndarray,
                   y_vals: np.ndarray,
                   mode: str = "ols",
                   lowess_frac: float = 0.3):
    """
    Devuelve (x_line, y_line, label) para la línea de tendencia elegida.
    mode: 'ols' | 'median' | 'theilsen' | 'lowess'
    lowess_frac: parámetro de suavizado (0.1–0.6 aprox.)
    """
    mask = np.isfinite(y_vals)
    x = x_pos[mask].astype(float)
    y = y_vals[mask].astype(float)

    if mask.sum() < 2:
        return None, None, None

    mode = mode.lower().strip()

    if mode == "median":
        med = float(np.median(y))
        return x_pos, np.full_like(x_pos, med, dtype=float), "Mediana"

    if mode == "theilsen":
        try:
            from scipy.stats import theilslopes
            slope, intercept, _, _ = theilslopes(y, x)
            y_hat = slope * x_pos + intercept
            return x_pos, y_hat, "Theil–Sen"
        except Exception as e:
            logger.warning(f"No se pudo usar Theil–Sen ({e}); caigo a OLS.")
            mode = "ols"  # fallback

    if mode == "lowess":
        try:
            from statsmodels.nonparametric.smoothers_lowess import lowess
            # LOWESS devuelve puntos solamente en x observados; interpolamos a x_pos
            lo = lowess(y, x, frac=lowess_frac, return_sorted=True)
            x_lo, y_lo = lo[:, 0], lo[:, 1]
            # Interpolación 1D sencilla al grid completo x_pos
            y_hat = np.interp(x_pos.astype(float), x_lo, y_lo)
            return x_pos, y_hat, f"LOWESS (frac={lowess_frac})"
        except Exception as e:
            logger.warning(f"No se pudo usar LOWESS ({e}); caigo a mediana.")
            med = float(np.median(y))
            return x_pos, np.full_like(x_pos, med, dtype=float), "Mediana"

    # default: OLS clásico
    a, b = np.polyfit(x, y, deg=1)
    y_hat = a * x_pos + b
    return x_pos, y_hat, f"OLS (pendiente={a:.3f})"


def _read_model_csv(csv_path: Path,
                    *,
                    units_filter: Optional[Iterable[str]] = ("mm^3",),
                    select: Optional[Iterable[str]] = None
                   ) -> pd.DataFrame:
    """
    Lee un CSV de modelo en el formato largo estándar:
      columnas requeridas: seccion, id_corto, descripcion, valor, unidad

    - units_filter: si no es None, filtra por esas unidades (por defecto solo 'mm^3')
    - select: iterable de id_corto a incluir (case-insensitive); si None, no filtra por nombres
    - Convierte 'valor' a numérico; descarta NaN con warning.
    - Deduplica por 'match_key':
        * Para corteza (seccion in {'lh.aparc','rh.aparc'}):  match_key = 'seccion:id_corto'
        * Resto (aseg/synthseg/clinical):                    match_key = 'id_corto'
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.error(f"No se pudo leer el CSV: {csv_path} ({e})")
        raise

    # Validación de columnas
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas en {csv_path}: {missing}")

    # Filtrar por unidad si se pide
    if units_filter is not None:
        df = df[df["unidad"].isin(units_filter)].copy()

    # Normalizar tipos/valores
    df["seccion"]  = df["seccion"].astype(str)
    df["id_corto"] = df["id_corto"].astype(str)
    df["valor"]    = pd.to_numeric(df["valor"], errors="coerce")

    # Quitar valores no numéricos
    n_bad = df["valor"].isna().sum()
    if n_bad:
        logger.warning(f"{csv_path.name}: {n_bad} fila(s) con 'valor' no numérico -> se omiten.")
        df = df.dropna(subset=["valor"]).copy()

    # Filtro select (case-insensitive) por id_corto
    if select:
        wanted = {s.lower().strip() for s in select}
        df = df[df["id_corto"].str.lower().isin(wanted)].copy()
        # Avisar los que faltaron del 'select'
        missing_select = sorted(wanted - set(df["id_corto"].str.lower().unique()))
        if missing_select:
            logger.warning(f"{csv_path.name}: {len(missing_select)} id(s) del 'select' no encontrados: {missing_select[:10]}{' ...' if len(missing_select)>10 else ''}")

    # -------- CLAVE DE EMPAREJAMIENTO --------
    sec_lower  = df["seccion"].str.lower().str.strip()
    name_lower = df["id_corto"].str.lower().str.strip()
    is_aparc   = sec_lower.isin({"lh.aparc", "rh.aparc"})

    # Para corteza: usar "seccion:id"
    match_key = name_lower.copy()
    match_key[is_aparc] = sec_lower[is_aparc] + ":" + name_lower[is_aparc]
    df["match_key"] = match_key

    # Deduplicar por match_key (no por id_corto)
    dup_mask = df.duplicated(subset=["match_key"], keep="first")
    n_dup = int(dup_mask.sum())
    if n_dup:
        logger.warning(f"{csv_path.name}: {n_dup} duplicado(s) por 'match_key' -> se conserva la primera aparición.")
        df = df[~dup_mask].copy()

    return df



def _compute_ratio_vs_ref(df_ref: pd.DataFrame, df_model: pd.DataFrame) -> pd.DataFrame:
    """
    Empareja df_ref (FreeSurfer) con df_model por 'match_key' y calcula:
      ratio = valor_modelo / valor_ref

    - Mantiene el orden de aparición del CSV de referencia (df_ref)
    - Descarta pares sin match con WARN
    - Conserva 'seccion' de referencia y del modelo (útil para etiquetar lh/rh)
    """
    ref = df_ref[["seccion", "id_corto", "match_key", "valor"]].rename(
        columns={"seccion": "seccion_ref", "valor": "valor_ref"}
    ).copy()
    mdl = df_model[["seccion", "id_corto", "match_key", "valor"]].rename(
        columns={"seccion": "seccion_model", "id_corto": "id_corto_model", "valor": "valor_modelo"}
    ).copy()

    merged = ref.merge(mdl, on="match_key", how="left", sort=False)

    # Avisos por faltantes
    n_missing = int(merged["valor_modelo"].isna().sum())
    if n_missing:
        faltan = merged.loc[merged["valor_modelo"].isna(), ["seccion_ref", "id_corto"]]
        ejemplos = [f"{row.seccion_ref}:{row.id_corto}" for _, row in faltan.head(10).iterrows()]
        logger.warning(
            f"El modelo no tiene {n_missing} estructura(s) presentes en FreeSurfer (se omiten). Ej: {ejemplos}{' ...' if n_missing>10 else ''}"
        )

    merged = merged.dropna(subset=["valor_modelo"]).copy()

    merged["ratio"] = merged["valor_modelo"] / merged["valor_ref"]

    # Armamos DF listo para graficar (con seccion_ref para etiquetar hemisferio)
    out = merged[[
        "seccion_ref", "id_corto", "valor_ref",
        "seccion_model", "id_corto_model", "valor_modelo",
        "ratio"
    ]].copy()
    return out



# ============================================================
# Graficado
# ============================================================
def _plot_ratio_scatter(df_ratio: pd.DataFrame,
                        *,
                        model_name: str,
                        color: str,
                        output_path: Path,
                        ylim: Tuple[float, float] = (0.0, 2.0),
                        trendline: bool = True,
                        trendline_style: Optional[Dict] = None,
                        trendline_mode: str = "median",   # 'median' | 'theilsen' | 'lowess' | 'ols'
                        lowess_frac: float = 0.3) -> None:
    """
    Scatter x=id_corto (FS), y=ratio (modelo/FS) y guarda PNG.
    trendline_mode: 'median' (recomendada), 'theilsen', 'lowess', 'ols'
    """
    if df_ratio.empty:
        logger.warning(f"[{model_name}] No hay datos para graficar (DF vacío).")
        return

    # Etiquetas de X con hemisferio para aparc
    def _label(row) -> str:
        sec = str(row.get("seccion_ref", "")).lower()
        name = str(row["id_corto"])
        if sec == "lh.aparc":
            return f"{name} (lh)"
        if sec == "rh.aparc":
            return f"{name} (rh)"
        return name

    x_labels = df_ratio.apply(_label, axis=1).tolist()
    y_vals   = df_ratio["ratio"].astype(float).to_numpy()
    x_pos    = np.arange(len(x_labels))

    plt.figure(figsize=(15, 6))
    plt.scatter(x_pos, y_vals, c=color, s=30, alpha=0.9, edgecolors="none")
    plt.axhline(1.0, linestyle="--", linewidth=1.5, color="black", alpha=0.8)

    # Línea de tendencia
    title_extra = ""
    if trendline:
        if trendline_style is None:
            trendline_style = {"color": "#444444", "linewidth": 2.0, "alpha": 0.95}
        x_line, y_line, lbl = _compute_trend(
            x_pos, y_vals, mode=trendline_mode, lowess_frac=lowess_frac
        )
        if x_line is not None:
            plt.plot(x_line, y_line, **trendline_style, label=lbl)
            title_extra = f" | {lbl}"
            
    std_val = np.std(y_vals)
    cv_val  = std_val / np.mean(y_vals) if np.mean(y_vals) != 0 else np.nan

    plt.title(f"Ratio de volúmenes: {model_name} vs FreeSurfer{title_extra}")
    # Mostrar métricas de dispersión en el gráfico
    disp_text = f"STD = {std_val:.3f}\nCV = {cv_val:.3f}"
    plt.text(
    0.58, 0.76, disp_text,
    transform=plt.gca().transAxes,  # usa coordenadas relativas al eje (0 a 1)
    fontsize=16,
    verticalalignment='bottom',
    horizontalalignment='right',
    bbox=dict(facecolor='white', edgecolor='gray', boxstyle='round,pad=0.3', alpha=0.8)
    )
    plt.xticks(x_pos, x_labels, rotation=90)
    plt.ylim(*ylim)
    plt.ylabel("Modelo / FreeSurfer")
    plt.xlabel("Estructura (id_corto)")

    handles, labels = plt.gca().get_legend_handles_labels()
    if handles:
        plt.legend(loc="upper right", frameon=False)

    plt.tight_layout()
    if not output_path.parent.exists():
        raise FileNotFoundError(f"La carpeta de salida no existe: {output_path.parent}")
    plt.savefig(output_path, dpi=300)
    plt.close()
    logger.info(f"[{model_name}] Gráfico guardado en: {output_path}")

# ============================================================
# Pipeline principal
# ============================================================
def graficar_modelos_vs_freesurfer(
    *,
    csv_freesurfer: Path,
    csv_fastsurfer: Path,
    csv_synthseg: Path,
    csv_clinical: Path,
    output_dir: Path,
    select: Optional[Iterable[str]] = None,
    units_filter: Optional[Iterable[str]] = ("mm^3",),
    colors: Optional[Dict[str, str]] = None,
    trendline: bool = 1,
    trendline_style: Optional[Dict] = None,
    trendline_mode:str
) -> None:
    """
    Genera 3 gráficos (FastSurfer, SynthSeg, Clinical) con ratio vs FreeSurfer.
    trendline: si True, dibuja recta de tendencia (OLS).
    trendline_style: dict matplotlib (p.ej. {"color":"#222","linewidth":3,"alpha":0.9})
    """
    if colors is None:
        colors = {
            "fastsurfer": "#1f77b4",
            "synthseg":   "#2ca02c",
            "clinical":   "#d62728",
        }

    # Leer CSV referencia
    df_fs = _read_model_csv(csv_freesurfer, units_filter=units_filter, select=select)

    # Leer y graficar cada modelo
    modelos = [
        ("fastsurfer", csv_fastsurfer, "scatter_fastsurfer3_vs_FS.png"),
        ("synthseg",   csv_synthseg,   "scatter_synthseg3_vs_FS.png"),
        ("clinical",   csv_clinical,   "scatter_clinical3_vs_FS.png"),
    ]

    for name, path_csv, fname in modelos:
        df_model = _read_model_csv(path_csv, units_filter=units_filter, select=select)
        df_ratio = _compute_ratio_vs_ref(df_fs, df_model)
        _plot_ratio_scatter(
            df_ratio,
            model_name=name,
            color=colors.get(name, "#333333"),
            output_path=output_dir / fname,
            ylim=(0.0, 2.0),
            trendline=trendline,
            trendline_style=trendline_style,
            trendline_mode=trendline_mode
        )
        logger.info(f"[{name}] Estructuras graficadas: {len(df_ratio)}")



# ============================================================
# Ejemplo de uso
# ============================================================
if __name__ == "__main__":
    # Reemplazá estas rutas por las tuyas
    csv_fs   = Path("/home/mbudani/results/procesamiento/volbrain/FS/csv_promedio.csv")
    csv_fast = Path("/home/mbudani/results/procesamiento/volbrain/fastsurfer/csv_promedio.csv")
    csv_ss   = Path("/home/mbudani/results/procesamiento/volbrain/synthseg/csv_promedio.csv")
    csv_cli  = Path("/home/mbudani/results/procesamiento/volbrain/clinical/csv_promedio.csv")

    out_dir  = Path("/home/mbudani/results/procesamiento/graficos/volbrain")  # la carpeta DEBE existir

    # Opción: graficar 
    #graficar_modelos_vs_freesurfer(
    #csv_freesurfer=csv_fs,
    #csv_fastsurfer=csv_fast,
    #csv_synthseg=csv_ss,
    #csv_clinical=csv_cli,
    #output_dir=out_dir,
    #select=None,
    #units_filter=("mm^3",),
    #trendline=True,
    # Elegí uno:
    # trendline_mode="median",
    # trendline_mode="theilsen",
    # trendline_mode="lowess",   # podés tunear smooth con lowess_frac=0.25
    #trendline_mode="median",
#)
    #Opción: graficar SOLO algunas estructuras (case-insensitive)
    graficar_modelos_vs_freesurfer(
          csv_freesurfer=csv_fs,
          csv_fastsurfer=csv_fast,
          csv_synthseg=csv_ss,
          csv_clinical=csv_cli,
          output_dir=out_dir,
          select=["eTIV", "Left-Thalamus", "Left-Caudate","insula","Left-Putamen", "Left-Pallidum","Left-Hippocampus","Left-Amygdala","Left-Accumbens-area","Right-Thalamus","Right-Caudate","Right-Putamen","Right-Pallidum","Right-Hippocampus","Right-Amygdala","Right-Accumbens-area","caudalanteriorcingulate","entorhinal","fusiform","inferiorparietal","lateralorbitofrontal","medialorbitofrontal","superiorfrontal","superiortemporal","insula","caudalanteriorcingulate","entorhinal","fusiform","inferiorparietal","lateralorbitofrontal","medialorbitofrontal","superiortemporal","insula"],
          units_filter=("mm^3",),
          trendline=True,
          trendline_mode="median"
    )