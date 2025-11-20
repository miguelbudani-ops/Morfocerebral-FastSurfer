from __future__ import annotations
from pathlib import Path
import os
import logging
from typing import Dict, Iterable, List, Optional, Tuple, Union, Set

import nibabel as nib
import numpy as np
import pandas as pd

# =========================
# Logging
# =========================
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("DICE-LUT")


# =========================
# LUT de FreeSurfer
# =========================
def locate_fs_lut(lut_path: Optional[Path] = None) -> Optional[Path]:
    """
    Intenta localizar el FreeSurferColorLUT.txt.
    Prioridad:
      1) lut_path explícito (si existe)
      2) $FREESURFER_HOME/FreeSurferColorLUT.txt
    """
    if lut_path is not None:
        lut_path = Path(lut_path)
        if lut_path.is_file():
            return lut_path

    fs_home = os.environ.get("FREESURFER_HOME", "")
    if fs_home:
        cand = Path(fs_home) / "FreeSurferColorLUT.txt"
        if cand.is_file():
            return cand

    return None


def load_fs_lut(lut_path: Optional[Path] = None) -> Dict[int, str]:
    """
    Carga LUT estándar de FreeSurfer y devuelve {label_id:int -> label_name:str}.
    Formato: id name R G B A (ignora comentarios '#').
    Si una etiqueta no está en LUT, luego usaremos 'UNKNOWN'.
    """
    path = locate_fs_lut(lut_path)
    if path is None:
        logger.warning("No se encontró FreeSurferColorLUT.txt; los nombres de etiquetas quedarán como 'UNKNOWN'.")
        return {}

    lut: Dict[int, str] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 6:
                continue
            try:
                id_ = int(parts[0])
                name_tokens = parts[1:-4] or [parts[1]]
                name = " ".join(name_tokens)
                lut[id_] = name
            except ValueError:
                continue
    return lut


# =========================
# Utilidad: resolver selección (IDs o nombres) a IDs
# =========================
def _resolve_requested_labels(
    select: Optional[Iterable[Union[int, str]]],
    lut: Dict[int, str]
) -> Set[int]:
    """
    Convierte una lista mixta de IDs o nombres LUT en un set de IDs.
    - Soporta ints, strings numéricos ('17'), o nombres de LUT (case-insensitive).
    - Si algún nombre no existe en el LUT -> ERROR (ValueError).
    """
    if not select:
        return set()

    name_to_id: Dict[str, int] = {name.lower(): id_ for id_, name in lut.items()}

    resolved: Set[int] = set()
    unknown_names: List[str] = []

    for item in select:
        if isinstance(item, int):
            resolved.add(int(item))
            continue
        s = str(item).strip()
        if s.isdigit():
            resolved.add(int(s))
            continue
        id_from_name = name_to_id.get(s.lower())
        if id_from_name is None:
            unknown_names.append(s)
        else:
            resolved.add(id_from_name)

    if unknown_names:
        msg = f"Las siguientes etiquetas por nombre no existen en el LUT: {unknown_names}"
        logger.error(msg)
        raise ValueError(msg)

    return resolved


# =========================
# Funcion original
# =========================
def calcular_dice_por_etiqueta(path_a, path_b):
    """
    Versión original: calcula DICE por etiqueta (UNIÓN de etiquetas).
    Mantengo esta función tal cual la compartiste, por compatibilidad con tu flujo previo.
    """
    data_a = nib.load(str(path_a)).get_fdata()
    data_b = nib.load(str(path_b)).get_fdata()

    if data_a.shape != data_b.shape:
        raise ValueError("Los volúmenes tienen dimensiones diferentes.")

    data_a = np.round(data_a).astype(np.int32)
    data_b = np.round(data_b).astype(np.int32)

    etiquetas = sorted(set(np.unique(data_a)) | set(np.unique(data_b)))
    resultados = {}

    for etiqueta in etiquetas:
        mask_a = (data_a == etiqueta)
        mask_b = (data_b == etiqueta)
        interseccion = np.logical_and(mask_a, mask_b).sum()
        suma = mask_a.sum() + mask_b.sum()
        if suma == 0:
            dice = np.nan
        else:
            dice = (2.0 * interseccion) / suma
        resultados[etiqueta] = dice

    return resultados


# =========================
# Nueva versión con LUT, intersección y selección
# =========================
def calcular_dice_por_etiqueta_v2(
    path_a: Union[str, Path],
    path_b: Union[str, Path],
    *,
    lut_path: Optional[Path] = None,
    select: Optional[Iterable[Union[int, str]]] = None,
    mode: str = "all",              # 'all' | 'include' | 'exclude'
    exclude_background: bool = True,
    dice_decimals: int = 3
) -> pd.DataFrame:
    """
    Calcula DICE por etiqueta SOLO en la INTERSECCIÓN de etiquetas presentes en ambos volúmenes,
    mapea cada ID a su nombre LUT, y aplica filtros por selección si se solicitan.
    Devuelve: DataFrame con columnas ['Etiqueta', 'Estructura', 'DICE'] (ordenado por Etiqueta).
    """
    path_a = Path(path_a)
    path_b = Path(path_b)

    lut = load_fs_lut(lut_path)

    img_a = nib.load(str(path_a))
    img_b = nib.load(str(path_b))
    data_a = np.round(img_a.get_fdata()).astype(np.int32)
    data_b = np.round(img_b.get_fdata()).astype(np.int32)

    if data_a.shape != data_b.shape:
        raise ValueError("Los volúmenes tienen dimensiones diferentes. Asegúrate de re-muestrear antes.")

    labels_a = set(np.unique(data_a).tolist())
    labels_b = set(np.unique(data_b).tolist())
    candidate_labels: Set[int] = labels_a & labels_b

    if exclude_background and 0 in candidate_labels:
        candidate_labels.discard(0)

    logger.info(f"Etiquetas presentes en ambos volúmenes (excluyendo fondo={exclude_background}): {len(candidate_labels)}")

    selected_ids: Set[int] = _resolve_requested_labels(select, lut) if select is not None else set()

    mode = mode.lower().strip()
    if mode not in {"all", "include", "exclude"}:
        raise ValueError("El parámetro 'mode' debe ser 'all', 'include' o 'exclude'.")

    if mode == "all":
        final_labels = set(candidate_labels)
    elif mode == "include":
        if not selected_ids:
            logger.warning("Modo 'include' sin 'select' definido: no hay etiquetas que incluir.")
            final_labels = set()
        else:
            final_labels = candidate_labels & selected_ids
    else:  # 'exclude'
        final_labels = candidate_labels - selected_ids

    if not final_labels:
        logger.warning("No hay etiquetas para evaluar tras aplicar filtros/mode.")
        return pd.DataFrame(columns=["Etiqueta", "Estructura", "DICE"])

    rows: List[Dict[str, Union[int, float, str]]] = []
    for lab in sorted(final_labels):
        mask_a = (data_a == lab)
        mask_b = (data_b == lab)
        n_a = int(mask_a.sum())
        n_b = int(mask_b.sum())
        if n_a == 0 or n_b == 0:
            logger.debug(f"Etiqueta {lab} sin voxeles en uno de los volúmenes; se omite.")
            continue

        interseccion = np.logical_and(mask_a, mask_b).sum()
        suma = n_a + n_b
        dice = (2.0 * interseccion) / suma if suma > 0 else np.nan

        rows.append({
            "Etiqueta": int(lab),
            "Estructura": lut.get(lab, "UNKNOWN"),
            "DICE": float(dice),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df.sort_values(by="Etiqueta", inplace=True)
        df["DICE"] = df["DICE"].round(dice_decimals)

    return df


# =========================
# Guardado CSV (acepta dict o DataFrame)
# =========================
def guardar_dice_como_csv(resultados, path_csv: Union[str, Path], lut_path: Optional[Path] = None):
    """
    Guarda resultados a CSV con columnas:
      - Etiqueta (id), Estructura (nombre LUT), DICE (3 decimales)
    'resultados' puede ser:
      - dict {id -> dice}
      - DataFrame con columnas ['Etiqueta','Estructura','DICE']
    """
    path_csv = Path(path_csv)

    if isinstance(resultados, dict):
        lut = load_fs_lut(lut_path)
        rows = []
        for k, v in resultados.items():
            try:
                lab = int(k)
            except Exception:
                continue
            rows.append({
                "Etiqueta": lab,
                "Estructura": lut.get(lab, "UNKNOWN"),
                "DICE": None if v is None else round(float(v), 3)
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df.sort_values(by="Etiqueta", inplace=True)
    elif isinstance(resultados, pd.DataFrame):
        df = resultados.copy()
        if "Etiqueta" in df.columns:
            df.sort_values(by="Etiqueta", inplace=True)
        if "DICE" in df.columns:
            df["DICE"] = df["DICE"].round(3)
    else:
        raise TypeError("resultados debe ser dict o pandas.DataFrame")

    path_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path_csv, index=False)
    logger.info(f"CSV guardado en: {path_csv}")


# ============================================================
# utilidades para procesamiento por lotes desde .txt
# ============================================================
def _read_paths_txt(txt_path: Union[str, Path]) -> List[Path]:
    """
    Lee un .txt con una ruta por línea. Ignora líneas vacías y comentarios (#).
    Devuelve lista de Path. Lanza ValueError si queda vacía.
    """
    txt_path = Path(txt_path)
    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.strip() for ln in f]
    except Exception as e:
        logger.error(f"No se pudo leer el archivo de rutas: {txt_path} ({e})")
        raise

    paths: List[Path] = []
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        p = Path(ln.strip())
        paths.append(p)

    if not paths:
        raise ValueError(f"{txt_path}: no se encontraron rutas válidas (archivo vacío o solo comentarios).")
    return paths


def _infer_subject_id(p: Path) -> str:
    """
    Heurística para extraer el ID de sujeto a partir de la ruta:
      - Si contiene '/mri/', usa el directorio anterior a 'mri' (estándar FreeSurfer).
      - Si no, usa el nombre del directorio padre.
      - Fallback: stem del archivo (sin extensión).
    """
    p = Path(p)
    parts = list(p.parts)
    try:
        idx = parts.index("mri")
        if idx > 0:
            return parts[idx - 1]
    except ValueError:
        pass
    if p.parent.name:
        return p.parent.name
    return p.stem


def _sanitize_filename(s: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in s)


def calcular_dice_batch_desde_txt(
    txt_refs: Union[str, Path],          # .txt con rutas a FS (referencia)
    txt_model: Union[str, Path],         # .txt con rutas al modelo (SynthSeg / FastSurfer / Clinical)
    out_dir: Union[str, Path],           # carpeta de salida (debe existir o se crea)
    *,
    model_name: str,
    lut_path: Optional[Path] = None,
    select: Optional[Iterable[Union[int, str]]] = None,
    mode: str = "all",
    exclude_background: bool = True,
    dice_decimals: int = 3,
    save_aggregate_csv: bool = True
) -> Path:
    """
    Procesa N pares (FS vs modelo) leídos desde dos .txt en el MISMO orden.
    - Genera un CSV por sujeto: columnas ['Etiqueta','Estructura','DICE'] (como tu función original).
    - Opcionalmente, también un CSV agregado con todas las filas (agrega columnas sujeto y modelo).

    Devuelve la ruta del CSV agregado si se generó, o la carpeta de salida si no.
    """
    txt_refs = Path(txt_refs)
    txt_model = Path(txt_model)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fs_paths = _read_paths_txt(txt_refs)
    mdl_paths = _read_paths_txt(txt_model)

    if len(fs_paths) != len(mdl_paths):
        raise ValueError(f"Las listas tienen distinto largo: FS={len(fs_paths)} vs Modelo={len(mdl_paths)}. "
                         "Asegúrate de que estén alineadas y en el mismo orden.")

    # Cargar LUT una sola vez
    lut = load_fs_lut(lut_path)

    agg_rows: List[Dict[str, Union[str, int, float]]] = []
    p=1
    for i, (fs_p, mdl_p) in enumerate(zip(fs_paths, mdl_paths), start=1):
        if not fs_p.is_file():
            logger.error(f"[{i}] No existe archivo FS: {fs_p}")
            continue
        if not mdl_p.is_file():
            logger.error(f"[{i}] No existe archivo del modelo: {mdl_p}")
            continue

        subject_id = _infer_subject_id(fs_p)
        subj_tag = _sanitize_filename(subject_id)
        mdl_tag = _sanitize_filename(model_name)

        logger.info(f"[{i}] Sujeto='{subject_id}' | FS='{fs_p.name}' vs {model_name}='{mdl_p.name}'")

        # Cálculo (misma lógica que v2; no modificado)
        try:
            df_subj = calcular_dice_por_etiqueta_v2(
                fs_p, mdl_p,
                lut_path=lut_path,      # se vuelve a cargar dentro; está bien por aislamiento
                select=select,
                mode=mode,
                exclude_background=exclude_background,
                dice_decimals=dice_decimals
            )
        except Exception as e:
            logger.error(f"[{i}] Error calculando DICE para '{subject_id}': {e}")
            continue

        # Guardado por sujeto (mismo formato)
        out_csv_subj = out_dir / f"dice_{p}_{mdl_tag}.csv"
        try:
            guardar_dice_como_csv(df_subj, out_csv_subj)
        except Exception as e:
            logger.error(f"[{i}] No se pudo guardar CSV de sujeto '{subject_id}': {e}")
        # Acumular para CSV agregado
        for _, row in df_subj.iterrows():
            agg_rows.append({
                "sujeto": p,
                "modelo": model_name,
                "Etiqueta": int(row["Etiqueta"]),
                "Estructura": str(row["Estructura"]),
                "DICE": float(row["DICE"]),
            })
        p=p+1
    if save_aggregate_csv:
        df_agg = pd.DataFrame(agg_rows, columns=["sujeto", "modelo", "Etiqueta", "Estructura", "DICE"])
        agg_path = out_dir / f"dice_{_sanitize_filename(model_name)}_agregado.csv"
        df_agg.to_csv(agg_path, index=False)
        logger.info(f"CSV agregado guardado en: {agg_path} (filas: {len(df_agg)})")
        return agg_path

    return out_dir


# ============================================================
# Ejemplo de uso por lotes (opcional)
# ============================================================
if __name__ == "__main__":
    # Archivos .txt con rutas alineadas (una ruta por línea, mismo orden):
    # txt_fs  : rutas a FS (referencia)
    # txt_ss  : rutas a SynthSeg (mismo orden que txt_fs)
    # txt_fast: rutas a FastSurfer (mismo orden que txt_fs)
    # txt_cli : rutas a Clinical (mismo orden que txt_fs)
    txt_fs   = Path("/home/mbudani/data/data_2021/to_fast/paths_fs_resampled_to_fast_2021.txt")
    txt_ss   = Path("/home/mbudani/results/synthseg_array_results/path_to_synthseg.txt")
    txt_fast = Path("/home/mbudani/results/fastsurfer_array_results_2021/path_to_fast_2021.txt")
    txt_cli  = Path("/home/mbudani/results/clinical_array_results/path_to_clinical.txt")

    out_dir  = Path("/home/mbudani/results/fastsurfer_array_results_2021/DICE")
    list_subcortex=[10,11,12,13,17,18,26,49,50,51,52,53,54,58]
    list_cortex=[1002,1006,1007,1008,1012,1014,1028,1030,1035,2002,2006,2007,2008,2012,2014,2030,2035],          # o, por ejemplo: [1002, 1006, "Left-Hippocampus"]
    # (ajustá select/mode si querés filtrar etiquetas)
    calcular_dice_batch_desde_txt(
        txt_refs=txt_fs,
        txt_model=txt_fast,
        out_dir=out_dir,
        model_name="clinical",
        select= [1002,1006,1007,1008,1012,1014,1028,1030,1035,2002,2006,2007,2008,2012,2014,2030,2035] ,                 # None o lista de IDs/nombres LUT
        mode="all",                  # 'all' | 'include' | 'exclude'
        exclude_background=True,
        dice_decimals=3,
        save_aggregate_csv=True,
        lut_path="/home/mbudani/apps/freesurfer/FreeSurferColorLUT.txt" 

    )
