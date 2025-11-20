from pathlib import Path
import logging
from typing import List, Tuple

import nibabel as nib
from nilearn.image import resample_to_img

# ============================================
# Logging
# ============================================
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("batch-resample")

# ============================================
# Utilidades
# ============================================
def _read_path_list(txt_path: Path) -> List[Path]:
    """
    Lee un archivo .txt con EXACTAMENTE una ruta por línea.
    No se permiten líneas vacías ni comentarios.
    Devuelve una lista de Path.
    """
    try:
        lines = txt_path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        logger.error(f"No se pudo leer el archivo: {txt_path} ({e})")
        raise

    paths: List[Path] = []
    for i, raw in enumerate(lines, start=1):
        s = raw.strip()
        if not s:
            raise ValueError(f"{txt_path}: línea {i} está vacía. Debe haber una ruta por línea.")
        if s.startswith("#"):
            raise ValueError(f"{txt_path}: línea {i} comienza con '#'. No se permiten comentarios; una ruta por línea.")
        p = Path(s)
        if not p.exists():
            raise FileNotFoundError(f"{txt_path}: línea {i} -> no existe el archivo: {p}")
        paths.append(p)
    return paths


def _strip_ext_nii_mgz(p: Path) -> str:
    """
    Devuelve el basename sin extensiones .nii, .nii.gz o .mgz
    """
    name = p.name
    if name.endswith(".nii.gz"):
        return name[:-7]
    if name.endswith(".nii"):
        return name[:-4]
    if name.endswith(".mgz"):
        return name[:-4]
    return p.stem  # fallback


def _next_non_clobber_path(base_out: Path) -> Path:
    """
    Si base_out no existe, lo devuelve. Si existe, agrega sufijos _v2, _v3, ...
    """
    if not base_out.exists():
        return base_out
    stem = base_out.stem
    suffix = base_out.suffix  # e.g. ".gz" cuando el nombre es ".nii.gz"? Ojo:
    # Path.stem con ".nii.gz" devuelve "nombre.nii", por lo que manejamos mejor manualmente:
    # Vamos a forzar la extensión final a ".nii.gz" siempre, y armamos sufijos sobre el "stem puro".
    # Solución: trabajar siempre con ".nii.gz".
    parent = base_out.parent
    pure = _strip_ext_nii_mgz(base_out)
    k = 2
    while True:
        cand = parent / f"{pure}_v{k}.nii.gz"
        if not cand.exists():
            return cand
        k += 1


# ============================================
# Resample batch
# ============================================
def batch_resample_fs_to_model(
    fs_txt: Path,
    model_txt: Path,
    out_dir: Path,
    out_txt_name: str = "paths_fs_resampled.txt"
) -> Tuple[int, int]:
    """
    Lee dos .txt (FS y Modelo), una ruta por línea (mismo orden y cantidad).
    Para cada par (fs_i, model_i):
      - resamplea fs_i al espacio de model_i (nearest)
      - guarda en out_dir con nombre: <basename_FS>_toMODELgrid.nii.gz
      - si existe, agrega sufijo incremental _v2, _v3, ...
    Al final, escribe en out_dir/<out_txt_name> las rutas resultantes (una por línea).
    Devuelve (n_ok, n_fail)
    """
    fs_txt = Path(fs_txt)
    model_txt = Path(model_txt)
    out_dir = Path(out_dir)

    # Comentario explícito para el usuario dentro del código:
    # -> Los .txt DEBEN contener UNA RUTA POR LÍNEA, sin líneas vacías ni comentarios.

    # Validar/cargar listas
    fs_paths = _read_path_list(fs_txt)
    model_paths = _read_path_list(model_txt)

    if len(fs_paths) != len(model_paths):
        msg = (f"Cantidad de líneas no coincide: FS={len(fs_paths)} | MODELO={len(model_paths)}. "
               f"Verificá los .txt (una ruta por línea, mismo orden).")
        logger.error(msg)
        raise ValueError(msg)

    # Crear carpeta de salida si no existe
    out_dir.mkdir(parents=True, exist_ok=True)

    out_txt_path = out_dir / out_txt_name
    saved_paths: List[Path] = []
    n_ok = 0
    n_fail = 0

    for idx, (fs_p, mdl_p) in enumerate(zip(fs_paths, model_paths), start=1):
        try:
            logger.info(f"[{idx}/{len(fs_paths)}] FS -> {fs_p.name}   |   Modelo -> {mdl_p.name}")

            img_fs = nib.load(str(fs_p))
            img_mdl = nib.load(str(mdl_p))

            # Resample a la grilla del modelo (nearest para etiquetas)
            res_img = resample_to_img(img_fs, img_mdl, interpolation="nearest")

            # Nombre de salida: basename(FS) + _toMODELgrid.nii.gz
            base_name = _strip_ext_nii_mgz(fs_p)
            out_path = out_dir / f"{base_name}_toMODELgrid.nii.gz"
            out_path = _next_non_clobber_path(out_path)

            nib.save(res_img, str(out_path))
            saved_paths.append(out_path)
            n_ok += 1
            logger.info(f"  ✓ guardado: {out_path}")

        except Exception as e:
            n_fail += 1
            logger.error(f"  ✗ error en el par {idx}: {e}")

    # Escribir TXT con rutas guardadas
    try:
        out_txt_content = "\n".join(str(p) for p in saved_paths)
        out_txt_path.write_text(out_txt_content + ("\n" if saved_paths else ""), encoding="utf-8")
        logger.info(f"Lista de rutas resampleadas guardada en: {out_txt_path}")
    except Exception as e:
        logger.error(f"No se pudo escribir el TXT de salida: {out_txt_path} ({e})")
        # no levantamos excepción para no perder el conteo, pero avisamos

    logger.info(f"Resample terminado. OK={n_ok} | FAIL={n_fail}")
    return n_ok, n_fail


# ============================================
# Ejemplo de uso
# ============================================
if __name__ == "__main__":
    # ==== IMPORTANTE: una ruta por línea, sin comentarios ni líneas vacías ====
    # Archivos .txt (mismo orden de sujetos en ambos):
    fs_txt_path    = Path("/home/mbudani/data/data_2021/path_to_FS_2021.txt")
    model_txt_path = Path("/home/mbudani/results/fastsurfer_array_results_2021/path_to_fast_2021.txt")  # synthseg/fastsurfer/clinical

    # Carpeta de salida (se creará si no existe)
    out_dir = Path("/home/mbudani/data/data_2021/to_fast")

    # Nombre del .txt con rutas resultantes (se guarda dentro de out_dir)
    out_list_name = "paths_fs_resampled_to_fast_2021.txt"

    batch_resample_fs_to_model(
        fs_txt=fs_txt_path,
        model_txt=model_txt_path,
        out_dir=out_dir,
        out_txt_name=out_list_name,
    )
