import subprocess
import os
from pathlib import Path
import sys
from PIL import Image


import nibabel as nib
import numpy as np

def _mask_world_centre(mask_paths):
    """Calcula el centroide en coordenadas de mundo a partir de máscaras NIfTI."""
    world_centres = []
    for path in mask_paths:
        if not path.exists():
            continue
        nii = nib.load(str(path))
        data = nii.get_fdata()
        vox_idx = np.argwhere(data > 0)
        if vox_idx.size == 0:
            continue
        world_coords = nib.affines.apply_affine(nii.affine, vox_idx)
        world_centres.append(world_coords.mean(axis=0))
    if not world_centres:
        return None
    centre = np.mean(world_centres, axis=0)
    return tuple(float(c) for c in centre)

def generate_macrostructure_plots_epilepsia(dicom_dir, subjects_dir):
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
        ("mask_hipocampo.nii",           (0.090, 0.305, 0.859)),
        ("mask_cuerpos_mamilares.nii",   (0.980, 0.623, 0.078)),
        ("mask_fornix.nii",              (0.643, 0.239, 0.792)),
    ]

    mask_layers = []
    mask_paths = []
    for filename, colour in mask_colours:
        mask_path = DIRECTORIO_MASCARAS / filename
        mask_layers.extend([
            str(mask_path),
            "-ot", "mask",
            "-a", "100",
            "-mc", f"{colour[0]:.4f}", f"{colour[1]:.4f}", f"{colour[2]:.4f}",
            "-o",
            "-w", "2",
        ])
        mask_paths.append(mask_path)

    capturas = {
        "macroestructuras_epilepsia.png": [
            str(IMAGEN_T1), "-dr", "0", MAX, "-in", "spline",
        ] + mask_layers,
    }

    world_centre = _mask_world_centre(mask_paths)

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
        ]

        if world_centre is not None:
            # Ajuste manual para centrar ligeramente anterior/superior
            ajuste = np.array([-3.0, -5.0, -8.0])
            loc = np.array(world_centre) + ajuste
            comando.extend(["--worldLoc"] + [f"{coord:.2f}" for coord in loc])

        comando += capas

        subprocess.run(comando, check=True)

    print("Todas las capturas se han generado exitosamente.")
