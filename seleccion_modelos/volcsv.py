from pathlib import Path
import logging
from typing import List, Dict, Tuple

import pandas as pd

# ============================================================================
# Logging
# ============================================================================
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("FS-stats-unificado")


# ============================================================================
# Utilidades
# ============================================================================
def _read_lines(path: Path) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
    except Exception as e:
        logger.error(f"No se pudo leer el archivo: {path} ({e})")
        raise


def _find_colheaders(lines: List[str]) -> Tuple[int, List[str]]:
    """
    Busca una línea que empiece con '# ColHeaders' y devuelve:
      - el índice de línea
      - la lista de nombres de columnas (split por espacios)
    Lanza ValueError si no la encuentra.
    """
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith("# ColHeaders"):
            # Ej: '# ColHeaders Index SegId NVoxels Volume_mm3 StructName'
            parts = line[len("# ColHeaders"):].strip().split()
            if not parts:
                raise ValueError("Línea '# ColHeaders' sin columnas.")
            return idx, parts
    raise ValueError("No se encontró '# ColHeaders' en el archivo.")


# ============================================================================
# Parsers específicos
# ============================================================================

def parse_aseg_measures(path: Path) -> pd.DataFrame:
    """
    Extrae *solo* las medidas globales especificadas desde 'aseg.stats',
    en líneas '# Measure <id_largo>, <id_corto>, <descripcion>, <valor>, <unidad>'.

    Sección: 'aseg.measures'
    Columnas: seccion, id_corto, descripcion, valor, unidad
    """
    REQUIRED_SHORT_IDS = {
        "lhCortexVol",
        "rhCortexVol",
        "lhCerebralWhiteMatterVol",
        "rhCerebralWhiteMatterVol",
        "eTIV",
    }

    lines = _read_lines(path)
    rows: List[Dict[str, object]] = []
    found_ids = set()
    total_lines = kept = skipped = 0

    for raw in lines:
        total_lines += 1
        line = raw.strip()
        if not line.lstrip().startswith("# Measure"):
            continue

        parts = [p.strip() for p in line.split(",")]
        # Esperamos al menos: [ '# Measure ...', short_id, descripcion, valor, unidad ]
        if len(parts) < 5:
            logger.warning(f"[aseg.measures] Línea malformada (se saltea): {line}")
            skipped += 1
            continue

        try:
            short_id = parts[1]
            descripcion = ", ".join(parts[2:-2]).strip()
            valor = float(parts[-2])
            unidad = parts[-1]
        except Exception as e:
            logger.warning(f"[aseg.measures] No se pudo parsear (se saltea): {line} | Error: {e}")
            skipped += 1
            continue

        # Guardar solo si es una de las requeridas
        if short_id in REQUIRED_SHORT_IDS:
            found_ids.add(short_id)
            rows.append({
                "seccion": "aseg.measures",
                "id_corto": short_id,
                "descripcion": descripcion,
                "valor": valor,
                "unidad": unidad
            })
            kept += 1

    # Avisar por las que faltaron (si alguna no apareció)
    missing = REQUIRED_SHORT_IDS - found_ids
    for m in sorted(missing):
        logger.warning(f"[aseg.measures] Medida solicitada no encontrada en aseg.stats: {m}")

    logger.info(f"[aseg.measures] medidas guardadas: {kept} | faltantes (warn): {len(missing)} | saltadas (malformadas): {skipped}")
    return pd.DataFrame(rows, columns=["seccion", "id_corto", "descripcion", "valor", "unidad"])


def parse_aseg_stats(path: Path) -> pd.DataFrame:
    """
    Lee aseg.stats detectando columnas por '# ColHeaders' y extrae:
      - id_corto: 'StructName'
      - valor: 'Volume_mm3'
      - unidad: 'mm^3'
      - descripcion: igual a id_corto
    Sección: 'aseg'
    """
    lines = _read_lines(path)
    try:
        header_idx, headers = _find_colheaders(lines)
    except ValueError as e:
        logger.error(f"[aseg] {e}")
        raise

    # Mapeo de columnas requeridas
    try:
        idx_struct = headers.index("StructName")
        idx_vol = headers.index("Volume_mm3")
    except ValueError:
        logger.error("[aseg] No se encontraron columnas requeridas: 'StructName' y 'Volume_mm3'")
        raise

    rows: List[Dict[str, object]] = []
    kept = skipped = 0

    # Parsear filas de datos: líneas posteriores al header que no empiezan con '#'
    for raw in lines[header_idx + 1:]:
        line = raw.strip()
        if (not line) or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < len(headers):
            logger.warning(f"[aseg] Fila corta (se saltea): {line}")
            skipped += 1
            continue

        try:
            struct_name = parts[idx_struct]
            vol_mm3 = float(parts[idx_vol])
        except Exception as e:
            logger.warning(f"[aseg] No se pudo parsear fila (se saltea): {line} | Error: {e}")
            skipped += 1
            continue
            # Lista de valores a saltar
        estructuras_a_ignorar = [
            "Left-vessel",
            "Left-choroid-plexus",
            "Right-vessel",
            "Right-choroid-plexus",
            "5th-Ventricle",
            "WM-hypointensities",
            "Left-WM-hypointensities",
            "Right-WM-hypointensities",
            "non-WM-hypointensities",
            "Left-non-WM-hypointensities",
            "Right-non-WM-hypointensities",
            "Optic-Chiasm",
            "CC_Posterior",
            "CC_Mid_Posterior",
            "CC_Central",
            "CC_Mid_Anterior",
            "CC_Anterior",
        ]


        if struct_name in estructuras_a_ignorar:
            skipped += 1
            continue

        rows.append({
                "seccion": "aseg",
                "id_corto": struct_name,
                "descripcion": struct_name,
                "valor": vol_mm3,
                "unidad": "mm^3"
            })
        kept += 1

    logger.info(f"[aseg] medidas guardadas: {kept} | saltadas: {skipped}")
    return pd.DataFrame(rows, columns=["seccion", "id_corto", "descripcion", "valor", "unidad"])


def parse_aparc_stats(path: Path, hemisphere_label: str) -> pd.DataFrame:
    """
    Lee lh.aparc.DKTatlas.stats o rh.aparc.DKTatlas.stats detectando columnas por '# ColHeaders' y extrae:
      - id_corto: 'StructName'
      - valor: 'GrayVol'
      - unidad: 'mm^3'
      - descripcion: igual a id_corto
    'hemisphere_label' se usa sólo para poner 'lh.aparc' o 'rh.aparc' en 'seccion'.
    """
    lines = _read_lines(path)
    try:
        header_idx, headers = _find_colheaders(lines)
    except ValueError as e:
        logger.error(f"[{hemisphere_label}] {e}")
        raise

    # Mapeo de columnas requeridas
    try:
        idx_struct = headers.index("StructName")
        idx_grayvol = headers.index("GrayVol")
    except ValueError:
        logger.error(f"[{hemisphere_label}] No se encontraron columnas requeridas: 'StructName' y 'GrayVol'")
        raise

    rows: List[Dict[str, object]] = []
    kept = skipped = 0

    for raw in lines[header_idx + 1:]:
        line = raw.strip()
        if (not line) or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < len(headers):
            logger.warning(f"[{hemisphere_label}] Fila corta (se saltea): {line}")
            skipped += 1
            continue

        try:
            struct_name = parts[idx_struct]
            grayvol = float(parts[idx_grayvol])
        except Exception as e:
            logger.warning(f"[{hemisphere_label}] No se pudo parsear fila (se saltea): {line} | Error: {e}")
            skipped += 1
            continue

        rows.append({
            "seccion": hemisphere_label,
            "id_corto": struct_name,
            "descripcion": struct_name,
            "valor": grayvol,
            "unidad": "mm^3"
        })
        kept += 1

    logger.info(f"[{hemisphere_label}] medidas guardadas: {kept} | saltadas: {skipped}")
    return pd.DataFrame(rows, columns=["seccion", "id_corto", "descripcion", "valor", "unidad"])


def parse_clinical_csv(path_csv: Path) -> pd.DataFrame:
    """
    Convierte el CSV clínico (SynthSeg) a formato largo:
      seccion='clinical.subcortical'
      id_corto = nombre de columna (mapeado a FreeSurfer si hay equivalencia)
      descripcion = igual a id_corto
      valor = numérico (si no puede convertirse, se saltea con warning)
      unidad = 'mm^3'

    Regla: incluir TODAS las columnas NO corticales:
      - Excluir columnas que comiencen con 'ctx-lh-' o 'ctx-rh-'
      - Excluir 'subject' (si existe)
    """
    try:
        df = pd.read_csv(path_csv)
    except Exception as e:
        logger.error(f"[clinical] No se pudo leer el CSV clínico: {path_csv} ({e})")
        raise

    if df.empty:
        logger.warning("[clinical] CSV clínico vacío.")
        return pd.DataFrame(columns=["seccion", "id_corto", "descripcion", "valor", "unidad"])

    # Equivalencias SynthSeg clinical -> FreeSurfer (búsqueda case-insensitive)
    _equiv_fs = {
        "total intracranial": "eTIV",
        "left cerebral white matter": "lhCerebralWhiteMatterVol",
        "left cerebral cortex": "lhCortexVol",
        "left lateral ventricle": "Left-Lateral-Ventricle",
        "left inferior lateral ventricle": "Left-Inf-Lat-Vent",
        "left cerebellum white matter": "Left-Cerebellum-White-Matter",
        "left cerebellum cortex": "Left-Cerebellum-Cortex",
        "left thalamus": "Left-Thalamus",
        "left caudate": "Left-Caudate",
        "left putamen": "Left-Putamen",
        "left pallidum": "Left-Pallidum",
        "3rd ventricle": "3rd-Ventricle",
        "4th ventricle": "4th-Ventricle",
        "brain-stem": "Brain-Stem",
        "left hippocampus": "Left-Hippocampus",
        "left amygdala": "Left-Amygdala",
        "left accumbens area": "Left-Accumbens-area",
        "left ventral dc": "Left-VentralDC",
        "right cerebral white matter": "rhCerebralWhiteMatterVol",
        "right cerebral cortex": "rhCortexVol",
        "right lateral ventricle": "Right-Lateral-Ventricle",
        "right inferior lateral ventricle": "Right-Inf-Lat-Vent",
        "right cerebellum white matter": "Right-Cerebellum-White-Matter",
        "right cerebellum cortex": "Right-Cerebellum-Cortex",
        "right thalamus": "Right-Thalamus",
        "right caudate": "Right-Caudate",
        "right putamen": "Right-Putamen",
        "right pallidum": "Right-Pallidum",
        "right hippocampus": "Right-Hippocampus",
        "right amygdala": "Right-Amygdala",
        "right accumbens area": "Right-Accumbens-area",
        "right ventral dc": "Right-VentralDC",
    }
    _equiv_fs = {k.lower(): v for k, v in _equiv_fs.items()}

    rows: List[Dict[str, object]] = []
    kept = skipped = 0

    for idx_row, row in df.iterrows():
        seen_ids: set[str] = set()  # para evitar duplicados tras mapeo en esta fila

        for col in df.columns:
            col_str = str(col).strip()
            col_norm = col_str.lower()

            # Exclusiones de columnas corticales y 'subject'
            if col_norm.startswith("ctx-lh-") or col_norm.startswith("ctx-rh-"):
                continue
            if col_norm == "subject":
                continue

            raw_val = row[col]
            # Intentar convertir a float
            try:
                val = pd.to_numeric(raw_val, errors="coerce")
                if pd.isna(val):
                    logger.warning(f"[clinical] Valor no numérico para columna '{col_str}' (se saltea). Fila {idx_row}")
                    skipped += 1
                    continue
            except Exception as e:
                logger.warning(f"[clinical] No se pudo convertir valor en '{col_str}' (se saltea). Error: {e}")
                skipped += 1
                continue

            # Aplicar equivalencia a nombre FreeSurfer (si existe)
            mapped_name = _equiv_fs.get(col_norm, col_str)

            # Evitar duplicados si dos columnas mapean al mismo nombre FS
            if mapped_name in seen_ids:
                logger.warning(
                    f"[clinical] Duplicado después de equivalencia: '{mapped_name}' (se saltea). Fila {idx_row}"
                )
                skipped += 1
                continue
            seen_ids.add(mapped_name)

            rows.append({
                "seccion": "clinical.subcortical",
                "id_corto": mapped_name,
                "descripcion": mapped_name,
                "valor": float(val),
                "unidad": "mm^3"
            })
            kept += 1

    logger.info(f"[clinical] filas guardadas: {kept} | saltadas: {skipped}")
        
        # Lista en el orden exacto que querés en la salida
    orden_fs = [
        "lhCortexVol",
        "rhCortexVol",
        "lhCerebralWhiteMatterVol",
        "rhCerebralWhiteMatterVol",
        "eTIV",
        "Left-Lateral-Ventricle",
        "Left-Inf-Lat-Vent",
        "Left-Cerebellum-White-Matter",
        "Left-Cerebellum-Cortex",
        "Left-Thalamus",
        "Left-Caudate",
        "Left-Putamen",
        "Left-Pallidum",
        "3rd-Ventricle",
        "4th-Ventricle",
        "Brain-Stem",
        "Left-Hippocampus",
        "Left-Amygdala",
        "CSF",
        "Left-Accumbens-area",
        "Left-VentralDC",
        "Left-vessel",
        "Left-choroid-plexus",
        "Right-Lateral-Ventricle",
        "Right-Inf-Lat-Vent",
        "Right-Cerebellum-White-Matter",
        "Right-Cerebellum-Cortex",
        "Right-Thalamus",
        "Right-Caudate",
        "Right-Putamen",
        "Right-Pallidum",
        "Right-Hippocampus",
        "Right-Amygdala",
        "Right-Accumbens-area",
        "Right-VentralDC"
    ]

    df_result = pd.DataFrame(rows, columns=["seccion", "id_corto", "descripcion", "valor", "unidad"])

    # Reordenar según lista, dejando lo que no esté al final
    df_result["orden_tmp"] = df_result["id_corto"].apply(lambda x: orden_fs.index(x) if x in orden_fs else len(orden_fs))
    df_result = df_result.sort_values("orden_tmp").drop(columns="orden_tmp").reset_index(drop=True)
    return df_result

def parse_SynthSeg_csv(path_csv: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path_csv)
    except Exception as e:
        logger.error(f"[SynthSeg] No se pudo leer el CSV clínico: {path_csv} ({e})")
        raise

    if df.empty:
        logger.warning("[SynthSeg] CSV clínico vacío.")
        return pd.DataFrame(columns=["seccion", "id_corto", "descripcion", "valor", "unidad"])
    rows: List[Dict[str, object]] = []
    kept = skipped = 0

    for idx_row, row in df.iterrows():
        seen_ids: set[str] = set()  # para evitar duplicados tras mapeo en esta fila

        for col in df.columns:
            col_str = str(col).strip()
            col_norm = col_str.lower()

            # Exclusiones de columnas corticales y 'subject'
            if not (col_norm.startswith("ctx-lh-") or col_norm.startswith("ctx-rh-")):
                continue
            if col_norm == "subject":
                continue
            raw_val = row[col]
            # Intentar convertir a float
            try:
                val = pd.to_numeric(raw_val, errors="coerce")
                if pd.isna(val):
                    logger.warning(f"[SynthSeg] Valor no numérico para columna '{col_str}' (se saltea). Fila {idx_row}")
                    skipped += 1
                    continue
            except Exception as e:
                logger.warning(f"[SynthSeg] No se pudo convertir valor en '{col_str}' (se saltea). Error: {e}")
                skipped += 1
                continue

            estructuras_a_ignorar = [
            "frontalpole",
            "temporalpole",
            "transversetemporal",
            "bankssts"
        ]


            if col_norm[7:] in estructuras_a_ignorar:
                skipped += 1
                continue
            if col_norm.startswith("ctx-lh-"):
                rows.append({
                    "seccion": "lh.aparc",
                    "id_corto": col_norm[7:],
                    "descripcion": col_norm[7:],
                    "valor": float(val),
                    "unidad": "mm^3"
                })
                kept += 1
            if col_norm.startswith("ctx-rh-"):
                rows.append({
                    "seccion": "rh.aparc",
                    "id_corto": col_norm[7:],
                    "descripcion": col_norm[7:],
                    "valor": float(val),
                    "unidad": "mm^3"
                })
                kept += 1

    logger.info(f"[clinical] filas guardadas: {kept} | saltadas: {skipped}")
    df_result = pd.DataFrame(rows, columns=["seccion", "id_corto", "descripcion", "valor", "unidad"])
    return df_result
            
# ============================================================================
# NUEVO: orquestador para clinical
# ============================================================================
def procesar_clinical(
    clinical_csv_path,
    lh_aparc_stats_path,
    rh_aparc_stats_path,
    output_csv_path
) -> None:
    """
    Genera un único CSV largo con columnas:
        seccion, id_corto, descripcion, valor, unidad
    Orden: clinical.subcortical -> lh.aparc -> rh.aparc

    - NO crea el directorio de salida: si no existe, lanza error.
    - Usa parse_clinical_csv + parse_aparc_stats.
    """
    clinical_csv_path = Path(clinical_csv_path)
    lh_aparc_stats_path = Path(lh_aparc_stats_path)
    rh_aparc_stats_path = Path(rh_aparc_stats_path)
    output_csv_path = Path(output_csv_path)

    # Validar existencia de carpeta de salida
    out_parent = output_csv_path.parent
    if not out_parent.exists():
        msg = f"La carpeta de salida no existe: {out_parent}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    # Parsear cada entrada
    df_clin = parse_clinical_csv(clinical_csv_path)
    df_lh = parse_aparc_stats(lh_aparc_stats_path, "lh.aparc")
    df_rh = parse_aparc_stats(rh_aparc_stats_path, "rh.aparc")

    # Concatenar en el orden solicitado
    df_final = pd.concat([df_clin, df_lh, df_rh], ignore_index=True)

    # Guardar CSV
    try:
        df_final.to_csv(output_csv_path, index=False)
    except Exception as e:
        logger.error(f"No se pudo guardar el CSV en {output_csv_path} ({e})")
        raise

    logger.info(f"Total filas guardadas: {len(df_final)}")
    print(f"Archivo CSV generado en: {output_csv_path}")

# ============================================================================
# orquestador para SynthSeg
# ============================================================================
def procesar_SynthSeg(
    SythSeg_csv_path,
    output_csv_path
) -> None:
    """
    Genera un único CSV largo con columnas:
        seccion, id_corto, descripcion, valor, unidad
    Orden: clinical.subcortical -> lh.aparc -> rh.aparc

    - NO crea el directorio de salida: si no existe, lanza error.
    - Usa parse_clinical_csv + parse_aparc_stats.
    """
    SythSeg_csv_path= Path(SythSeg_csv_path)
    output_csv_path = Path(output_csv_path)

    # Validar existencia de carpeta de salida
    out_parent = output_csv_path.parent
    if not out_parent.exists():
        msg = f"La carpeta de salida no existe: {out_parent}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    # Parsear cada entrada
    df_seg= parse_clinical_csv(SythSeg_csv_path)
    df_ctx= parse_SynthSeg_csv(SythSeg_csv_path)

    # Concatenar en el orden solicitado
    df_final = pd.concat([df_seg, df_ctx], ignore_index=True)

    # Guardar CSV
    try:
        df_final.to_csv(output_csv_path, index=False)
    except Exception as e:
        logger.error(f"No se pudo guardar el CSV en {output_csv_path} ({e})")
        raise

    logger.info(f"Total filas guardadas: {len(df_final)}")
    print(f"Archivo CSV generado en: {output_csv_path}")

# ============================================================================
# Orquestador
# ============================================================================
def procesar_todo(
    aseg_stats_path,
    lh_aparc_stats_path,
    rh_aparc_stats_path,
    output_csv_path
) -> None:
    """
    Genera un único CSV largo con columnas:
        seccion, id_corto, descripcion, valor, unidad
    Orden: aseg.measures -> aseg -> lh.aparc -> rh.aparc

    - NO crea el directorio de salida: si no existe, lanza error.
    - Loggea conteos por sección y total final.
    """
    aseg_stats_path = Path(aseg_stats_path)
    lh_aparc_stats_path = Path(lh_aparc_stats_path)
    rh_aparc_stats_path = Path(rh_aparc_stats_path)
    output_csv_path = Path(output_csv_path)

    # Validar existencia de carpeta de salida
    out_parent = output_csv_path.parent
    if not out_parent.exists():
        msg = f"La carpeta de salida no existe: {out_parent}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    # Parsear cada archivo (en el orden solicitado)
    df_aseg_measures = parse_aseg_measures(aseg_stats_path)
    df_aseg = parse_aseg_stats(aseg_stats_path)
    df_lh = parse_aparc_stats(lh_aparc_stats_path, "lh.aparc")
    df_rh = parse_aparc_stats(rh_aparc_stats_path, "rh.aparc")

    # Concatenar en orden requerido
    df_final = pd.concat(
        [df_aseg_measures, df_aseg, df_lh, df_rh],
        ignore_index=True
    )

    # Guardar CSV
    try:
        df_final.to_csv(output_csv_path, index=False)
    except Exception as e:
        logger.error(f"No se pudo guardar el CSV en {output_csv_path} ({e})")
        raise

    logger.info(f"Total filas guardadas: {len(df_final)}")
    print(f"Archivo CSV generado en: {output_csv_path}")

# Leer rutas desde los archivos
def leer_rutas(path_txt):
    with path_txt.open("r", encoding="utf-8") as archivo:
        return [Path(linea.strip()) for linea in archivo if linea.strip()]

def batch_procesar_todo(txt_aseg, dir_salida, modelo: str, txt_lha=None, txt_rha=None):

    """
    Ejecuta el procesamiento por lotes de sujetos en función del modelo especificado.

    Esta función toma rutas a archivos `.txt` que contienen paths a archivos de entrada
    (por sujeto), y genera archivos de salida `.csv` numerados secuencialmente en un
    directorio destino. El comportamiento varía según el modelo elegido.

    Parámetros:
    ----------
    txt_aseg : str or Path
        Ruta al archivo `.txt` que contiene los paths a los archivos aseg por sujeto.
    dir_salida : str or Path
        Directorio donde se guardarán los archivos de salida generados.
    modelo : str
        Tipo de procesamiento a aplicar. Debe ser uno de:
        - "synthseg" → usa solo aseg
        - "FS", "fast" → usa aseg, lha y rha
        - "clinical" → usa aseg, lha y rha
    txt_lha : str or Path, opcional
        Ruta al archivo `.txt` con paths a los archivos lha por sujeto. Requerido si el modelo no es "synthseg".
    txt_rha : str or Path, opcional
        Ruta al archivo `.txt` con paths a los archivos rha por sujeto. Requerido si el modelo no es "synthseg".

    Comportamiento:
    --------------
    - Valida que las listas de rutas tengan la misma longitud si el modelo requiere múltiples entradas.
    - Crea el directorio de salida si no existe.
    - Genera archivos de salida con nombre `csvvol_<modelo>_<p>.csv`, donde `p` es el índice del sujeto.
    - Llama a la función correspondiente según el modelo:
        - `procesar_SynthSeg()` para "synthseg"
        - `procesar_todo()` para "FS" y "fast"
        - `procesar_clinical()` para "clinical"

    Consideraciones:
    ---------------
    - Los archivos `.txt` deben contener una ruta por línea, sin espacios extra ni líneas vacías.
    - Si se usa logging, los mensajes de procesamiento se registran por sujeto.
    - La función está diseñada para integrarse fácilmente en pipelines reproducibles y defensivos.

    Ejemplo de uso:
    --------------
    batch_procesar_todo(
        txt_aseg="rutas_aseg.txt",
        txt_lha="rutas_lha.txt",
        txt_rha="rutas_rha.txt",
        dir_salida="resultados/",
        modelo="FS"
    )
    """

    txt_aseg = Path(txt_aseg)
    dir_salida = Path(dir_salida)
    dir_salida.mkdir(parents=True, exist_ok=True)

    rutas_aseg = leer_rutas(txt_aseg)

    if modelo == "synthseg":
        for p, aseg in enumerate(rutas_aseg, start=1):
            nombre_archivo = f"csvvol_{modelo}_{p}.csv"
            ruta_salida = dir_salida / nombre_archivo
            logging.info(f"🔄 Procesando sujeto {p}")
            procesar_SynthSeg(aseg, ruta_salida)
        return

    # Leer rutas opcionales
    rutas_lha = leer_rutas(Path(txt_lha)) if txt_lha else []
    rutas_rha = leer_rutas(Path(txt_rha)) if txt_rha else []

    if modelo in ("FS", "fast", "clinical"):
        if not (len(rutas_aseg) == len(rutas_lha) == len(rutas_rha)):
            raise ValueError("❌ Las listas de rutas no tienen la misma longitud")

    for p, (aseg, lha, rha) in enumerate(zip(rutas_aseg, rutas_lha, rutas_rha), start=1):
        nombre_archivo = f"csvvol_{modelo}_{p}.csv"
        ruta_salida = dir_salida / nombre_archivo

        if modelo in ("FS", "fast"):
            logging.info(f"🔄 Procesando sujeto {p}")
            procesar_todo(aseg, lha, rha, ruta_salida)
        elif modelo == "clinical":
            logging.info(f"🔄 Procesando sujeto {p}")
            procesar_clinical(aseg, lha, rha, ruta_salida)


if __name__ == "__main__":
    # FAST / clinical/ FreeSurfer-like (aseg + lh.aparc + rh.aparc)
    #SynthSeg solo csv

    #fast
    batch_procesar_todo(
        txt_aseg="/home/mbudani/results/fastsurfer_array_results/path_fastsurfer_stats_aseg.txt",
        dir_salida="/home/mbudani/results/procesamiento/volbrain/fastsurfer",
        modelo="fast", 
        txt_lha="/home/mbudani/results/fastsurfer_array_results/path_fastsurfer_stats_lhaparc.txt", 
        txt_rha="/home/mbudani/results/fastsurfer_array_results/path_fastsurfer_stats_rhaparc.txt",
    )
    #free
    batch_procesar_todo(
        txt_aseg="/home/mbudani/results/freesurfer_array_results/path_freesurfer_stats_aseg.txt",
        dir_salida="/home/mbudani/results/procesamiento/volbrain/FS",
        modelo="FS", 
        txt_lha="/home/mbudani/results/freesurfer_array_results/path_freesurfer_stats_lhaparc.txt", 
        txt_rha="/home/mbudani/results/freesurfer_array_results/path_freesurfer_stats_rhaparc.txt",
    )
    #clinical    
    batch_procesar_todo(
        txt_aseg="/home/mbudani/results/clinical_array_results/path_clinical_stats_volcsv.txt",
        dir_salida="/home/mbudani/results/procesamiento/volbrain/clinical",
        modelo="clinical", 
        txt_lha="/home/mbudani/results/clinical_array_results/path_clinical_stats_lhaparc.txt", 
        txt_rha="/home/mbudani/results/clinical_array_results/path_clinical_stats_rhaparc.txt",
    )

    # SynthSeg (solo CSV)
    batch_procesar_todo(
        txt_aseg="/home/mbudani/results/synthseg_array_results/path_synthseg_stats_volcsv.txt",
        dir_salida="/home/mbudani/results/procesamiento/volbrain/synthseg",
        modelo="synthseg"
    )
