import subprocess
import os
from pathlib import Path
import sys
from PIL import Image

def generate_macrostructure_plots_especificos(dicom_dir, subjects_dir):
    # Definir las rutas
    DIRECTORIO_T1 = Path(dicom_dir)
    DIRECTORIO_FREESURFER = Path(subjects_dir)
    DIRECTORIO_MASCARAS = DIRECTORIO_FREESURFER / "mri" / "mask"

    DIRECTORIO_MASCARAS.mkdir(parents=True, exist_ok=True)

    # Buscar el archivo .nii en el directorio T1
    nii_files = list(DIRECTORIO_T1.glob('*.nii'))
    if not nii_files:
        raise FileNotFoundError("No se encontró ningún archivo con la extensión .nii en el directorio proporcionado.")
    IMAGEN_T1 = nii_files[0]

    # Calcular el rango dinámico robusto de la imagen T1
    rango = subprocess.check_output(["fslstats", str(IMAGEN_T1), "-r"]).decode('utf-8').strip()
    MIN, MAX = rango.split()
    MAX = str(float(MAX) + 1000)

    # -------------------------
    # Definir combinaciones de capas
    # -------------------------
    mask_colours = [
        ("mask_amigdala.nii",            (0.643, 0.239, 0.792)),
        ("mask_ganglios_basales.nii",    (0.000, 0.631, 0.612)),
        ("mask_hipocampo.nii",           (0.090, 0.305, 0.859)),
        ("mask_lobulo_frontal.nii",      (0.980, 0.623, 0.078)),
        ("mask_lobulo_occipital.nii",    (0.282, 0.827, 0.188)),
        ("mask_lobulo_parietal.nii",     (0.984, 0.803, 0.172)),
        ("mask_lobulo_temporal.nii",     (0.043, 0.478, 0.839)),
        ("mask_talamo.nii",              (0.698, 0.298, 0.698)),
        ("mask_ventriculos_laterales.nii",(0.000, 0.733, 0.925)),
    ]

    mask_layers = []
    for filename, colour in mask_colours:
        mask_layers.extend([
            str(DIRECTORIO_MASCARAS / filename),
            "-ot", "mask",
            "-a", "100",
            "-mc", f"{colour[0]:.4f}", f"{colour[1]:.4f}", f"{colour[2]:.4f}",
            "-o",
            "-w", "2",
        ])

    capturas = {
        "macroestructuras_especificos.png": [
            str(IMAGEN_T1), "-dr", "0", MAX, "-in", "spline",
        ] + mask_layers,
    }

    # -------------------------
    # Ejecutar fsleyes render para cada una
    # -------------------------
    for nombre_archivo, capas in capturas.items():
        output_screenshot = DIRECTORIO_MASCARAS / nombre_archivo
        comando = [
            "fsleyes", "render",
            "-of", str(output_screenshot),
            "--size", "2000", "700",
            "--scene", "ortho",
            "--worldLoc", "10", "5", "0"
        ] + capas

        subprocess.run(comando, check=True)

    print("Todas las capturas se han generado exitosamente.")
