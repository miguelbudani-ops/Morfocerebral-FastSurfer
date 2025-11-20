from __future__ import annotations#sirve para activar una caracteristica futura del lenguaje, en este caso hace que las anotaciones de tipo Dict, List, etc se interpreten como strings y se resuelvan luego en lugar de interpretarse inmediatamente. Esto sirve cuando se requieren uusar datos o funciones que no estan completamente soportados en la version actual de python.
from pathlib import Path
import os #permite interactuar con el sistema operativo, en nuestro caso nos sirve para buscar freesurfer home
import logging #Es un sistema de logging configurable: en vez de imprimir con print(), usás logging.info(), logging.warning(), logging.error().Ventajas: podés controlar niveles de detalle, guardar en archivos, etc.
from typing import Dict, Iterable, List, Optional, Tuple#typing provee tipos estáticos para mejorar la legibilidad y ayudar a herramientas como linters o editores inteligentes (no cambia la ejecución en runtime).
from typing import Union, Set
import numpy as np
import nibabel as nib
from nibabel.affines import apply_affine
from scipy import ndimage
from scipy.spatial import cKDTree
import pandas as pd


# ============================================================
# Configuración básica de logging (logs informativos en consola)
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger("HD95")

# ============================================
# Batch HD95 desde dos TXT (refs y preds)
# ============================================
def _read_paths_txt(txt_path: Union[str, Path]) -> List[Path]:
    """
    Lee rutas (una por línea) desde un TXT.
    NOTA: Debe haber estrictamente UNA ruta por línea (sin comas ni comentarios).
    Líneas vacías se ignoran.
    """
    txt_path = Path(txt_path)
    if not txt_path.is_file():
        raise FileNotFoundError(f"No existe el TXT: {txt_path}")
    paths: List[Path] = []
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        for ln, raw in enumerate(f, start=1):
            s = raw.strip()
            if not s:
                continue  # ignoramos líneas vacías
            paths.append(Path(s))
    return paths

def load_label_image(path: Path) -> Tuple[nib.spatialimages.SpatialImage, np.ndarray, np.ndarray]:
    #En cuanto a la flecha indica que la funcion retorna una tupla, nib.spatialimages.SpatialImage es el primer valor de la tupl
    #Es un objeto de nibabel que crea el cargador de iamgenes .nii o .mgz, este objeto contien tanto los datos de la imagen como la cabecera.
    #el segundo valor de la tupla es un array multidimensional int32 donde se guardaran los valores de la segmentacion
    #le tercer valor en la tupla es también un array NumPy que contiene la matriz afín (matriz 4x4) asociada con la imagen. Esta matriz transforma las coordenadas del índice del voxel (i, j, k) en coordenadas espaciales (mm), es decir, convierte los índices de voxel en unidades físicas del espacio.
    #Es decir a la funcion le ingreso la direccion a una imagen segmentada y me devuelve una tupla con 
    #Los valores de la iamgen, los valores de las segmentaciones y una matriz para pasar a coordenadas espaciales.
    """
    Carga una imagen etiquetada (label map) en formato .mgz / .nii 
    y devuelve: (objeto nibabel, array de datos int32, matriz afín 4x4).
    - get_fdata() convierte a float64 por defecto -> luego lo pasamos a int32.
    - Redondeamos antes por seguridad numérica (p.ej. 2.0000001 -> 2).
    """
    img = nib.load(str(path))#carga el path de la imagen en un archivo de nibabel
    #img es un objeto de tipo SpatialImage de nibabel, que contiene tanto los datos de 
    # #la imagen (los valores numéricos de los voxeles) como la información de la cabecera (dimensiones, affine, etc.).
    data = img.get_fdata()               # ndarray en float64
    data = np.round(data).astype(np.int32)
    #get_fdata() es un método de los objetos SpatialImage en nibabel que extrae los datos de la imagen.
    #get_fdata() devuelve los datos de la imagen como un array NumPy (np.ndarray), y por defecto, los convierte en tipo float64. Este es un tipo de dato numérico que permite una mayor precisión.
    # En el caso de imágenes de segmentación (etiquetas), get_fdata() carga todos los valores de los voxeles de la imagen en un formato flotante, pero los valores de las etiquetas son enteros, así que los convertimos después.
    affine = img.affine                  # 4x4, lleva de (i,j,k,1) a mm
    #img.affine: Es la matriz afín que está asociada con la imagen cargada. Es una matriz 
    # 4x4 que transforma las coordenadas de índice de voxel (i, j, k) (que son índices de
    #  la matriz de la imagen) a coordenadas espaciales en milímetros (mm).
    # la matriz afín define cómo se relacionan las coordenadas del volumen con el espacio
    #  físico de la imagen. Esta matriz es crucial cuando trabajamos con imágenes médicas 
    # porque nos permite conocer la ubicación física de cada voxel en el espacio
    return img, data, affine

# ============================================================
# Superficies: conectividad 26 vía erosión binaria + XOR
# ============================================================
def make_surface(mask: np.ndarray) -> np.ndarray:
    """
    Obtiene la 'superficie' de una máscara binaria 3D:
      surface = mask & (~erode(mask))
    Usamos conectividad 26 en 3D (estructura 3x3x3 de unos).
    """
    if not mask.any():
        # Máscara vacía -> superficie vacía.
        return np.zeros_like(mask, dtype=bool)

    # Estructura de conectividad 26 en 3D:
    # generate_binary_structure(rank=3, connectivity=3) -> 26-neigh.
    structure = ndimage.generate_binary_structure(rank=3, connectivity=3)
    eroded = ndimage.binary_erosion(mask, structure=structure, iterations=1, border_value=0)
    surface = mask & (~eroded)
    return surface


# ============================================================
# Distancias entre superficies en milímetros (KDTree en mm)
# ============================================================
def surface_points_mm(surface_mask: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """
    Devuelve un array (N,3) con coordenadas en MILÍMETROS de los voxeles
    que pertenecen a la superficie (surface_mask=True), aplicando el afín.
    """
    idx = np.argwhere(surface_mask)  # (N,3) en índices IJK
    if idx.size == 0:
        return np.empty((0, 3), dtype=float)
    # Pasar de índices IJK a coordenadas físicas (mm) con el afín 4x4
    xyz_mm = apply_affine(affine, idx)  # (N,3)
    return xyz_mm


def directed_surface_distances_mm(points_src_mm: np.ndarray, points_dst_mm: np.ndarray) -> np.ndarray:
    """
    Distancias dirigidas de cada punto src a su vecino más cercano en dst (en mm).
    Usa cKDTree por eficiencia.
    Si dst está vacío, devuelve un array vacío (se manejará aguas arriba).
    """
    if points_src_mm.shape[0] == 0:
        return np.empty((0,), dtype=float)
    if points_dst_mm.shape[0] == 0:
        # No hay destino: por contrato superior, no deberíamos estar aquí
        # si filtramos etiquetas ausentes, pero por seguridad:
        return np.full((points_src_mm.shape[0],), np.inf, dtype=float)

    tree = cKDTree(points_dst_mm)
    dists, _ = tree.query(points_src_mm, k=1, workers=-1)
    return dists  # en milímetros


def hd50_hd95_hdmax_bidirectional_mm(points_A_mm: np.ndarray, points_B_mm: np.ndarray) -> Tuple[float, float, float]:
    """
    Calcula HD50, HD95 y HDmax bidireccionales:
      - Distancias A->B y B->A (superficie a superficie)
      - Toma percentiles 50 y 95 y máximo sobre el conjunto combinado.
    Devuelve (hd50_mm, hd95_mm, hdmax_mm).
    """
    d_AB = directed_surface_distances_mm(points_A_mm, points_B_mm)
    d_BA = directed_surface_distances_mm(points_B_mm, points_A_mm)

    # Unir ambas direcciones
    all_d = np.concatenate([d_AB, d_BA])

    # Si por algún motivo no hay puntos, devolvemos NaN
    if all_d.size == 0 or not np.isfinite(all_d).any():
        return (np.nan, np.nan, np.nan)

    hd50 = float(np.percentile(all_d[np.isfinite(all_d)], 50))
    hd95 = float(np.percentile(all_d[np.isfinite(all_d)], 95))
    hdmax = float(np.max(all_d[np.isfinite(all_d)]))
    return (hd50, hd95, hdmax)

def _resolve_requested_labels(
    select: Optional[Iterable[Union[int, str]]],
    lut: Dict[int, str]
) -> Set[int]:
    """
    Convierte una lista mixta de IDs (int) o nombres (str) del LUT en un set de IDs.
    - Coincidencia EXACTA por nombre (case-insensitive).
    - Strings numéricos ('17') también se aceptan como IDs.
    - Si algún nombre no está en el LUT -> ValueError (y logger.error).
    """
    if not select:
        return set()

    # nombre_lower -> id
    name_to_id: Dict[str, int] = {name.lower(): lid for lid, name in lut.items()}

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
        # nombre exacto (case-insensitive)
        lid = name_to_id.get(s.lower())
        if lid is None:
            unknown_names.append(s)
        else:
            resolved.add(lid)

    if unknown_names:
        msg = f"Las siguientes etiquetas por nombre no existen en el LUT: {unknown_names}"
        logger.error(msg)
        raise ValueError(msg)

    return resolved

# ============================================================
# LUT de FreeSurfer: mapeo id -> nombre (opcional pero recomendado)
# ============================================================
def locate_fs_lut(lut_path: Optional[Path] = None) -> Optional[Path]:
    """
    Intenta localizar el FreeSurferColorLUT.txt.
    Prioridad:
      1) lut_path pasado por parámetro (si existe)
      2) $FREESURFER_HOME/FreeSurferColorLUT.txt
    Si no se encuentra, devuelve None.
    """
    if lut_path is not None and Path(lut_path).is_file():
        return Path(lut_path)

    fs_home = os.environ.get("FREESURFER_HOME", "")
    if fs_home:
        cand = Path(fs_home) / "FreeSurferColorLUT.txt"
        if cand.is_file():
            return cand

    return None


def load_fs_lut(lut_path: Optional[Path] = None) -> Dict[int, str]:
    """
    Carga el LUT estándar de FreeSurfer y devuelve {label_id:int -> label_name:str}.
    Ignora líneas comentadas (#) y parsea 'id name R G B A'.
    El 'name' puede tener guiones; si tuviera espacios, tomamos todo entre id y RGBA.
    """
    path = locate_fs_lut(lut_path)
    if path is None:
        logger.warning("No se encontró FreeSurferColorLUT.txt; los nombres de etiquetas quedarán vacíos.")
        return {}

    lut: Dict[int, str] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            # Debe haber al menos 6 columnas: id name R G B A
            if len(parts) < 6:
                continue
            try:
                # Los últimos 4 tokens son RGBA -> el nombre puede ser 1 o más tokens
                id_ = int(parts[0])
                name_tokens = parts[1:-4]
                if not name_tokens:
                    name_tokens = [parts[1]]
                name = " ".join(name_tokens)
                lut[id_] = name
            except ValueError:
                continue
    return lut

def compute_hd_metrics_per_label(
    ref_path: Path,
    pred_path: Path,
    out_csv: Path,
    lut_path: Optional[Path] = None,
    min_voxels: int = 50,          # umbral para filtrar etiquetas "minúsculas"
    verbose: bool = True,
    *,
    select: Optional[Iterable[Union[int, str]]] = None,  # NUEVO: IDs o nombres LUT
    mode: str = "all"                                    # NUEVO: 'all' | 'include' | 'exclude'
) -> pd.DataFrame:
    """
    Calcula HD50/HD95/HDmax por etiqueta entre ref (p.ej., FreeSurfer) y pred (p.ej., SynthSeg).
    Reglas existentes:
      - Si shapes difieren -> resampleo pred a la rejilla de ref (nearest).
      - Distancias en mm (usando afines).
      - Evaluar TODAS las etiquetas != 0, pero:
          * excluir fondo (0)
          * excluir etiquetas con < min_voxels en ref o pred
          * excluir etiquetas NO presentes en ambos
      - Superficie por erosión (conectividad 26).
      - Exporto CSV con columnas detalladas.

    NUEVO:
      - Filtro de etiquetas por 'select' + 'mode' tras aplicar las reglas anteriores.
        * 'all': ignora 'select'
        * 'include': usa solo intersección con 'select'
        * 'exclude': quita las de 'select'
      - 'select' admite IDs (int) y/o nombres LUT (str). Nombres exactos (case-insensitive).
      - Si se pasa un nombre que no existe en LUT -> ValueError.
    """
    # Cargar LUT (si está disponible)
    lut = load_fs_lut(lut_path)

    # Cargar referencia (FreeSurfer) y predicción (modelo)
    ref_img, ref_data, ref_affine = load_label_image(ref_path)
    pred_img, pred_data, pred_affine = load_label_image(pred_path)

    # Candidatas (unión) y excluir fondo (0)
    labels_ref = np.unique(ref_data)
    labels_pred = np.unique(pred_data)
    candidate_labels = sorted(set(labels_ref) | set(labels_pred))
    candidate_labels = [int(l) for l in candidate_labels if l != 0]

    logger.info(f"Candidatas (excluyendo 0): {len(candidate_labels)}")

    # PRIMER PASO: aplicar reglas existentes -> presencia en ambos y min_voxels
    valid_labels: List[int] = []
    sizes_ref: Dict[int, int] = {}
    sizes_pred: Dict[int, int] = {}

    for lab in candidate_labels:
        n_ref = int((ref_data == lab).sum())
        n_pred = int((pred_data == lab).sum())

        # Reglas: presentes en ambos
        if n_ref == 0 or n_pred == 0:
            if verbose:
                logger.info(f"Label {lab} ausente en uno de los volúmenes -> se omite.")
            continue

        # Reglas: tamaño mínimo
        if n_ref < min_voxels or n_pred < min_voxels:
            if verbose:
                logger.info(f"Label {lab} filtrada por tamaño: n_ref={n_ref}, n_pred={n_pred} (< {min_voxels})")
            continue

        valid_labels.append(lab)
        sizes_ref[lab] = n_ref
        sizes_pred[lab] = n_pred

    logger.info(f"Tras reglas (presencia/min_voxels) => etiquetas válidas: {len(valid_labels)}")

    # SEGUNDO PASO (NUEVO): aplicar 'select' + 'mode'
    mode_norm = mode.lower().strip()
    if mode_norm not in {"all", "include", "exclude"}:
        raise ValueError("El parámetro 'mode' debe ser 'all', 'include' o 'exclude'.")

    if mode_norm == "all" or not select:
        final_labels = set(valid_labels)
        logger.info(f"Selección: mode='all' (o select vacío) -> {len(final_labels)} etiquetas.")
    else:
        selected_ids = _resolve_requested_labels(select, lut)  # puede lanzar ValueError si hay nombres desconocidos
        if mode_norm == "include":
            final_labels = set(valid_labels) & selected_ids
            logger.info(f"Selección: mode='include' -> {len(final_labels)} etiquetas (de {len(valid_labels)} válidas).")
        else:  # 'exclude'
            final_labels = set(valid_labels) - selected_ids
            logger.info(f"Selección: mode='exclude' -> {len(final_labels)} etiquetas (de {len(valid_labels)} válidas).")

    if not final_labels:
        logger.warning("No hay etiquetas para evaluar tras aplicar select/mode.")
        df_empty = pd.DataFrame(columns=[
            "label_id","label_name","n_vox_ref","n_vox_pred","n_surf_ref","n_surf_pred","hd50_mm","hd95_mm","hdmax_mm"
        ])
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        df_empty.to_csv(out_csv, index=False)
        logger.info(f"CSV guardado en: {out_csv}")
        return df_empty

    # TERCER PASO: cálculo métrico (idéntico a lo que ya hacías)
    rows: List[Dict[str, object]] = []

    for lab in sorted(final_labels):
        # Máscaras binarias
        mask_ref = (ref_data == lab)
        mask_pred = (pred_data == lab)

        # Superficies (conectividad 26)
        surf_ref = make_surface(mask_ref)
        surf_pred = make_surface(mask_pred)

        n_surf_ref = int(surf_ref.sum())
        n_surf_pred = int(surf_pred.sum())

        if n_surf_ref == 0 or n_surf_pred == 0:
            if verbose:
                logger.info(f"Label {lab}: superficie vacía en uno de los volúmenes -> se omite.")
            continue

        # Coordenadas de superficie en mm (aplicando afines propios)
        pts_ref_mm = surface_points_mm(surf_ref, ref_affine)
        pts_pred_mm = surface_points_mm(surf_pred, pred_affine)

        # Distancias bidireccionales -> HD50 / HD95 / HDmax
        hd50, hd95, hdmax = hd50_hd95_hdmax_bidirectional_mm(pts_ref_mm, pts_pred_mm)

        rows.append({
            "label_id": lab,
            "label_name": lut.get(lab, ""),  # si no está, quedará vacío (como antes)
            "n_vox_ref": sizes_ref.get(lab, int((ref_data == lab).sum())),
            "n_vox_pred": sizes_pred.get(lab, int((pred_data == lab).sum())),
            "n_surf_ref": n_surf_ref,
            "n_surf_pred": n_surf_pred,
            "hd50_mm": hd50,
            "hd95_mm": hd95,
            "hdmax_mm": hdmax,
        })

        #if verbose:
         #   logger.info(f"Label {lab} ({lut.get(lab, '')}): HD95 = {hd95:.3f} mm")

    # DataFrame y guardado a CSV
    df = pd.DataFrame(rows)
    if not df.empty:
        df.sort_values(by="label_id", inplace=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    logger.info(f"CSV guardado en: {out_csv}")
    return df

def batch_hd95_from_txt(
    refs_txt: Union[str, Path],
    preds_txt: Union[str, Path],
    out_dir: Union[str, Path],
    *,
    lut_path: Optional[Path] = None,
    min_voxels: int = 50,
    verbose: bool = True,
    select: Optional[Iterable[Union[int, str]]] = None,
    mode: str = "all",
) -> Optional[pd.DataFrame]:
    """
    Procesa N pares (ref, pred) leídos de dos TXT (una ruta por línea, mismo orden).
    Por cada par:
      - Ejecuta compute_hd_metrics_per_label (cálculo HD50/HD95/HDmax por etiqueta).
      - Guarda un CSV por sujeto en 'out_dir' con nombre 'hd95_<basename_ref>.csv'.
    Al final:
      - Genera 'hd95_combined.csv' con una columna 'subject_id' (basename del ref).

    Comportamiento y validaciones:
      - Aborta si la cantidad de líneas en ambos TXT no coincide.
      - Si un par falla, lo reporta (logging.error) y continúa con el resto.
      - 'select' y 'mode' se aplican igual para todos los sujetos.
      - LUT: usa FREESURFER_HOME por defecto, o 'lut_path' si se proporciona.

    Devuelve:
      - DataFrame combinado (si hubo al menos un sujeto exitoso); de lo contrario, None.
    """
    refs = _read_paths_txt(refs_txt)
    preds = _read_paths_txt(preds_txt)

    if len(refs) != len(preds):
        raise ValueError(
            f"Cantidad de líneas diferente entre refs ({len(refs)}) y preds ({len(preds)}). "
            f"Ambos TXT deben tener el MISMO número de rutas."
        )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    combined: List[pd.DataFrame] = []
    total = len(refs)
    logger.info(f"[BATCH HD95] Pares a procesar: {total}")

    for i, (ref_path, pred_path) in enumerate(zip(refs, preds), start=1):
        subject_id = ref_path.stem  # usamos el basename del archivo de referencia
        out_csv = out_dir / f"hd95_{subject_id}.csv"

        #logger.info(f"[{i}/{total}] Procesando sujeto '{subject_id}'")
        try:
            df = compute_hd_metrics_per_label(
                ref_path=ref_path,
                pred_path=pred_path,
                out_csv=out_csv,
                lut_path=lut_path,
                min_voxels=min_voxels,
                verbose=verbose,
                select=select,
                mode=mode,
            )
            if df is not None and not df.empty:
                df2 = df.copy()
                df2.insert(0, "subject_id", subject_id)
                combined.append(df2)
            else:
                logger.warning(f"[{subject_id}] DataFrame vacío. Revisa si hubo filtros que dejaron sin etiquetas.")
        except Exception as e:
            logger.error(f"[{subject_id}] Error durante el procesamiento: {e}")
            continue

    if not combined:
        logger.warning("[BATCH HD95] No se generó ningún resultado. No se creará el CSV combinado.")
        return None

    df_comb = pd.concat(combined, ignore_index=True)
    combined_csv = out_dir / "hd95_combined.csv"
    df_comb.to_csv(combined_csv, index=False)
    logger.info(f"[BATCH HD95] CSV combinado guardado en: {combined_csv}")
    return df_comb


# ============================================
# Ejemplo de uso (puedes ajustarlo o comentar)
# ============================================
if __name__ == "__main__":
    # Deben ser TXT con UNA ruta por línea (mismo orden y misma cantidad de líneas).
    refs_txt  = "/home/mbudani/data/data_2021/to_fast/paths_fs_resampled_to_fast_2021.txt"   # ← cada línea: /ruta/a/freesurfer_resampleado_X.nii.gz
    preds_txt = "/home/mbudani/results/fastsurfer_array_results_2021/path_to_fast_2021.txt"  # ← cada línea: /ruta/a/modelo_X.nii.gz

    out_dir   = "/home/mbudani/results/fastsurfer_array_results_2021/HD95"  # aquí se guardarán los CSV por sujeto y el combinado
    list_subcortex=[10,11,12,13,17,18,26,49,50,51,52,53,54,58]
    list_cortex=[1002,1006,1007,1008,1012,1014,1028,1030,1035,2002,2006,2007,2008,2012,2014,2030,2035],          # o, por ejemplo: [1002, 1006, "Left-Hippocampus"]
    # Ejecutar batch (mismos parámetros para todos los sujetos)
    batch_hd95_from_txt(
        refs_txt=refs_txt,
        preds_txt=preds_txt,
        out_dir=out_dir,
        lut_path="/home/mbudani/apps/freesurfer/FreeSurferColorLUT.txt",        # usa el LUT de $FREESURFER_HOME por defecto
        min_voxels=50,
        verbose=True,
        select=[1002,1006,1007,1008,1012,1014,1028,1030,1035,2002,2006,2007,2008,2012,2014,2030,2035],          # o, por ejemplo: [1002, 1006, "Left-Hippocampus"]
        mode="all",           # 'all' | 'include' | 'exclude'
    )
