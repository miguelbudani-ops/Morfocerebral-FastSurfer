#!/usr/bin/env python
# coding: utf-8

import os
import subprocess

def generate_stats_tables(dicom_dir):
    """
    Genera tablas estadísticas a partir de los archivos .stats de FastSurfer.

    :param dicom_dir: Ruta al directorio base que contiene la subcarpeta 'FreeSurfer' 
                      (o en este caso, la salida de FastSurfer).
    """
    # Asumo que la estructura de salida de fastsurfer tiene el sujeto "1"
    # como lo tenías en tu script original.
    subjects_dir = os.path.join(dicom_dir, "FastSurfer")
    stats_dir = os.path.join(subjects_dir, "stats")

    if not os.path.exists(stats_dir):
        raise RuntimeError(f"No se encontró el directorio 'stats' en: {stats_dir}")

    # ¡Importante! SUBJECTS_DIR debe apuntar al directorio que CONTIENE 
    # la carpeta del sujeto "1". En tu script original apuntaba a dicom_dir.
    # Si "1" está dentro de dicom_dir, esto es correcto.
    os.environ["SUBJECTS_DIR"] = dicom_dir 
    print(f"\nSUBJECTS_DIR configurado en: {os.environ['SUBJECTS_DIR']}\n")

    measures = ["thickness", "area", "foldind","volume"]  # <- agrega 'volume' (GrayVol)
    hemispheres = ["lh", "rh"]
    
    # --- INICIO DE LA MODIFICACIÓN ---
    # Este es el nombre de la parcelación de FastSurfer
    parcellation_name = "aparc.DKTatlas.mapped"
    # --- FIN DE LA MODIFICACIÓN ---

    logs = []  # Lista para almacenar la salida de los comandos

    # Crear tablas para medidas corticales
    for measure in measures:
        for hemi in hemispheres:
            # (Opcional) Cambié el nombre del archivo de salida para que sea más claro
            output_file = os.path.join(stats_dir, f"{hemi}_{parcellation_name}_{measure}_stats.txt")
            
            # --- INICIO DE LA MODIFICACIÓN ---
            # Agregamos el flag --parc
            command = (
                f"aparcstats2table --subjects FastSurfer --transpose --hemi {hemi} "
                f"--parc {parcellation_name} "
                f"--meas {measure} --tablefile {output_file}"
            )
            # --- FIN DE LA MODIFICACIÓN ---
            
            logs.append(f"Ejecutando: {command}")
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            logs.append(result.stdout)
            logs.append(result.stderr)

    # Crear tablas para volúmenes subcorticales (ESTA PARTE QUEDA IGUAL)
    aseg_files = {
        "aseg_stats_etiv.txt": "--meas volume --etiv",
        "aseg_stats_cm3.txt": "--meas volume --scale=0.001"
    }
    for output_file, params in aseg_files.items():
        full_path = os.path.join(stats_dir, output_file)
        command = f"asegstats2table --subjects FastSurfer --transpose {params} --tablefile {full_path}"
        logs.append(f"Ejecutando: {command}")
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        logs.append(result.stdout)
        logs.append(result.stderr)
        
    # Imprimir todo el log de una sola vez
    print("\n".join(filter(None, logs)))

    print("Tablas generadas con éxito.")