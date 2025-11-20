#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Consolidación de volúmenes de FastSurfer en cohorte.

Entradas:
  - Archivo .txt con rutas absolutas a CSVs (uno por línea).
    Cada CSV debe tener columnas: 'Estructura', 'Volumen_mm3', 'Volumen_rel_eTIV'.

Salidas:
  - CSV con promedios por estructura: 'Estructura, mean_mm3, mean_rel_eTIV'.
  - Diccionario por estructura con listas de valores absolutos y relativos
    (JSON por defecto si --out-dict termina en .json; opcionalmente CSV largo).

Uso:
  python consolidar_cohorte.py --paths lista_csvs.txt --out-means mean_vols.csv --out-dict dict_vals.json

  python promedio_estructuras_interes.py \
  --paths /home/mbudani/results/estructuras_de_interes/rutas_estructuras_interes.txt \
  --out-means /home/mbudani/results/estructuras_de_interes/mean_vols.csv \
  --out-dict /home/mbudani/results/estructuras_de_interes/dict_vals.json
"""

from __future__ import annotations
import argparse
import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


# ---------------------------- Utilidades de E/S ---------------------------- #

def file_must_exist(path: Path, kind: str) -> None:
    """
    Verifica existencia de un archivo; emite error claro si falta.
    """
    if not path.exists():
        raise FileNotFoundError(f"No existe el {kind}: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"No es un archivo {kind}: {path}")


def read_paths_file(paths_txt: Path) -> List[Path]:
    """
    Lee un .txt con rutas absolutas a CSV (una por línea).
    - Ignora líneas vacías y comentarios ('#').
    - Quita duplicados preservando orden.
    - Emite warnings por rutas inexistentes o no-CSV.
    """
    file_must_exist(paths_txt, "archivo .txt de rutas")

    lines = paths_txt.read_text(encoding="utf-8-sig").splitlines()
    seen = set()
    result: List[Path] = []
    for i, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        p = Path(line)
        if p.as_posix() in seen:
            warnings.warn(f"[Línea {i}] Ruta duplicada ignorada: {p}")
            continue
        if not p.exists() or not p.is_file():
            warnings.warn(f"[Línea {i}] No existe el archivo CSV: {p}")
            continue
        if p.suffix.lower() != ".csv":
            warnings.warn(f"[Línea {i}] No es .csv, se ignora: {p}")
            continue
        seen.add(p.as_posix())
        result.append(p)

    if not result:
        raise ValueError("El archivo de rutas no contiene CSVs válidos.")
    return result


# ---------------------------- Carga y validación --------------------------- #

REQUIRED_COLS = ("Estructura", "Volumen_mm3", "Volumen_rel_eTIV")

def _normalize_columns(cols: List[str]) -> Dict[str, str]:
    """
    Genera un mapeo flexible para renombrar columnas a los nombres requeridos.
    Intenta ser tolerante con mayúsculas/espacios/acentos comunes.
    """
    import unicodedata
    def simplifica(s: str) -> str:
        s0 = unicodedata.normalize("NFKD", s)
        s0 = "".join(c for c in s0 if not unicodedata.combining(c))
        s0 = s0.strip().lower().replace(" ", "_")
        s0 = s0.replace("³", "3")
        return s0

    target_map = {
        "estructura": "Estructura",
        "volumen_mm3": "Volumen_mm3",
        "volumen_rel_etiv": "Volumen_rel_eTIV",
        "volumen_rel_etiv_": "Volumen_rel_eTIV",
        "volumen_rel__etiv": "Volumen_rel_eTIV",
    }
    mapping = {}
    for c in cols:
        sc = simplifica(c)
        if sc in target_map:
            mapping[c] = target_map[sc]
    return mapping


def _to_numeric_safe(series: pd.Series, colname: str) -> pd.Series:
    """
    Convierte a numérico tolerando coma decimal y strings; advierte por NaNs creados.
    """
    s = series.astype(str).str.replace(",", ".", regex=False)
    num = pd.to_numeric(s, errors="coerce")
    n_bad = num.isna().sum()
    if n_bad:
        warnings.warn(f"Se encontraron {n_bad} valores no numéricos en '{colname}' que serán ignorados.")
    return num


def load_one_csv(path: Path) -> pd.DataFrame:
    """
    Carga un CSV individual y asegura columnas requeridas y tipos.
    - Renombra columnas si detecta variantes.
    - Fuerza numéricos en mm3 y rel_eTIV (coma decimal aceptada).
    - Elimina filas con Estructura nula o ambas métricas NaN.
    """
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")

    # Normalizar/renombrar columnas
    rename_map = _normalize_columns(df.columns.tolist())
    if rename_map:
        df = df.rename(columns=rename_map)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV sin columnas requeridas {missing} → {path}")

    # Tipos
    df["Estructura"] = df["Estructura"].astype(str).str.strip()
    df["Volumen_mm3"] = _to_numeric_safe(df["Volumen_mm3"], "Volumen_mm3")
    df["Volumen_rel_eTIV"] = _to_numeric_safe(df["Volumen_rel_eTIV"], "Volumen_rel_eTIV")

    # Filtrado básico
    before = len(df)
    df = df[~df["Estructura"].isna() & ~(df["Estructura"].str.strip() == "")]
    if len(df) < before:
        warnings.warn(f"{before - len(df)} filas sin 'Estructura' eliminadas en {path}")

    # Si una de las dos métricas falta, se mantiene la otra (servirá para promedios parciales);
    # sólo se descarta fila si ambas son NaN
    before2 = len(df)
    df = df[~(df["Volumen_mm3"].isna() & df["Volumen_rel_eTIV"].isna())]
    if len(df) < before2:
        warnings.warn(f"{before2 - len(df)} filas sin métricas válidas eliminadas en {path}")

    # Anexar metadato de fuente (opcional, por trazabilidad)
    df["__source_csv__"] = path.as_posix()
    return df[["Estructura", "Volumen_mm3", "Volumen_rel_eTIV", "__source_csv__"]]


def load_all_csvs(paths: List[Path]) -> pd.DataFrame:
    """
    Carga todos los CSVs, emitiendo warnings si alguno falla.
    Retorna un único DataFrame consolidado.
    """
    frames: List[pd.DataFrame] = []
    for p in paths:
        try:
            df = load_one_csv(p)
            frames.append(df)
        except Exception as e:
            warnings.warn(f"No se pudo procesar {p}: {e}")
    if not frames:
        raise RuntimeError("No se pudo cargar ningún CSV válido.")
    return pd.concat(frames, ignore_index=True)


# ---------------------------- Agregaciones -------------------------------- #

def build_value_dict(df: pd.DataFrame) -> Dict[str, Dict[str, List[float]]]:
    """
    Construye el diccionario {estructura: {"Volumen_mm3": [...], "Volumen_rel_eTIV": [...]}}.
    Solo incluye valores no-NaN en cada lista.
    """
    out: Dict[str, Dict[str, List[float]]] = {}
    for estructura, g in df.groupby("Estructura", dropna=False):
        mm3_vals = g["Volumen_mm3"].dropna().astype(float).tolist()
        rel_vals = g["Volumen_rel_eTIV"].dropna().astype(float).tolist()
        out[str(estructura)] = {
            "Volumen_mm3": mm3_vals,
            "Volumen_rel_eTIV": rel_vals,
        }
    return out


def compute_means(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula promedios por estructura.
    - mean_mm3: promedio de Volumen_mm3 (ignorando NaN)
    - mean_rel_eTIV: promedio de Volumen_rel_eTIV (ignorando NaN)
    """
    agg = (
        df.groupby("Estructura", as_index=False)
          .agg(mean_mm3=("Volumen_mm3", "mean"),
               mean_rel_eTIV=("Volumen_rel_eTIV", "mean"))
          .sort_values("Estructura")
          .reset_index(drop=True)
    )
    return agg


# ---------------------------- Guardado ------------------------------------- #

def save_means_csv(means_df: pd.DataFrame, out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    means_df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"[OK] Guardado promedios: {out_csv}")


def save_dict(dict_values: Dict[str, Dict[str, List[float]]], out_path: Path) -> None:
    """
    Guarda el diccionario:
      - Si termina en .json → JSON con indentación.
      - Si termina en .csv  → formato largo: Estructura,Tipo,Valor (una fila por valor).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".json":
        out_path.write_text(json.dumps(dict_values, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] Guardado diccionario JSON: {out_path}")
    elif out_path.suffix.lower() == ".csv":
        rows = []
        for estructura, d in dict_values.items():
            for v in d.get("Volumen_mm3", []):
                rows.append({"Estructura": estructura, "Tipo": "Volumen_mm3", "Valor": v})
            for v in d.get("Volumen_rel_eTIV", []):
                rows.append({"Estructura": estructura, "Tipo": "Volumen_rel_eTIV", "Valor": v})
        pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8")
        print(f"[OK] Guardado diccionario CSV largo: {out_path}")
    else:
        raise ValueError(f"Extensión no soportada para --out-dict: {out_path.suffix}. Use .json o .csv.")


# ---------------------------- CLI principal -------------------------------- #

@dataclass
class Args:
    paths: Path
    out_means: Path
    out_dict: Path


def parse_args() -> Args:
    ap = argparse.ArgumentParser(
        description="Consolidar CSVs de volúmenes FastSurfer, promediar por estructura y exportar diccionario de valores."
    )
    ap.add_argument("--paths", required=True, type=Path,
                    help="Ruta al .txt con rutas absolutas a CSVs (uno por línea).")
    ap.add_argument("--out-means", required=True, type=Path,
                    help="Ruta de salida para CSV de promedios por estructura (e.g., mean_vols.csv).")
    ap.add_argument("--out-dict", required=True, type=Path,
                    help="Ruta de salida para el diccionario (.json recomendado; .csv produce formato largo).")
    ns = ap.parse_args()
    return Args(paths=ns.paths, out_means=ns.out_means, out_dict=ns.out_dict)


def main() -> None:
    args = parse_args()

    # 1) Leer rutas
    csv_paths = read_paths_file(args.paths)
    print(f"[INFO] CSVs válidos encontrados: {len(csv_paths)}")

    # 2) Cargar y consolidar
    df_all = load_all_csvs(csv_paths)
    print(f"[INFO] Filas totales consolidadas: {len(df_all)}")

    # 3) Construir diccionario de listas
    dict_values = build_value_dict(df_all)

    # 4) Calcular promedios por estructura
    means_df = compute_means(df_all)

    # 5) Guardar salidas
    save_means_csv(means_df, args.out_means)
    save_dict(dict_values, args.out_dict)

    # 6) Resumen
    n_structs = means_df["Estructura"].nunique()
    print(f"[OK] Estructuras procesadas: {n_structs}")
    print("[DONE] Consolidación y guardado completados.")


if __name__ == "__main__":
    # Opcional: trate warnings como visibles
    warnings.simplefilter("default", category=UserWarning)
    main()
