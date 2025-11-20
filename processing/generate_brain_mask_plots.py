import subprocess
import os
from pathlib import Path
import sys
from PIL import Image

def generate_macrostructure_plots(dicom_dir, subjects_dir):
    # Definir las rutas
    DIRECTORIO_T1 = Path(dicom_dir)
    DIRECTORIO_FREESURFER = Path(subjects_dir)
    DIRECTORIO_APARC_ASEG = DIRECTORIO_FREESURFER / "mri"
    DIRECTORIO_MESH = DIRECTORIO_FREESURFER / "surf"
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
    # Generar wm.png
    # -------------------------
    output_wm = DIRECTORIO_MASCARAS / "wm.png"
    comando_wm = [
        "fsleyes", "render",
        "-of", str(output_wm),
        "--size", "2000", "700",
        "--scene", "ortho",
        "--worldLoc", "10", "5", "0",

        str(IMAGEN_T1), "-dr", "0", MAX, "-in", "spline",
        str(DIRECTORIO_MASCARAS / "mask_brain_stem.nii"), "-ot", "mask", "-a", "0", "-mc", "1.0", "0.6471", "0.0",
        str(DIRECTORIO_MESH / "rh.white"), "-ot", "mesh", "--outline", "--outlineWidth", "1.0", "-w", "1.3", "-mc", "1.0", "1.0", "0.0",
        str(DIRECTORIO_MESH / "lh.white"), "-ot", "mesh", "--outline", "--outlineWidth", "1.0", "-w", "1.3", "-mc", "1.0", "1.0", "0.0"
    ]
    subprocess.run(comando_wm, check=True)

    # -------------------------
    # Definir combinaciones de capas
    # -------------------------
    capturas = {
        "macroestructuras.png": [
            str(IMAGEN_T1), "-dr", "0", MAX, "-in", "spline",
            str(DIRECTORIO_MASCARAS / "mask_hemisferio_izquierdo.nii"), "-ot", "mask", "-a", "22", "-mc", "1.0", "0.0", "0.4431",
            str(DIRECTORIO_MASCARAS / "mask_hemisferio_derecho.nii"), "-ot", "mask", "-a", "22", "-mc", "0.0", "0.8431", "1.0",
            str(DIRECTORIO_MASCARAS / "mask_cerebelo.nii"), "-ot", "mask", "-a", "30", "-mc", "0.2314", "0.5686", "0.2314",
            str(DIRECTORIO_MASCARAS / "mask_brain_stem.nii"), "-ot", "mask", "-a", "25", "-mc", "1.0", "0.6471", "0.0",
            str(DIRECTORIO_MASCARAS / "mask_cuerpo_calloso.nii"), "-ot", "mask", "-a", "25", "-mc", "0.5", "0.0", "0.5"
        ],
        "aseg.png": [
            str(IMAGEN_T1), "-dr", "0", MAX, "-in", "spline",
            str(DIRECTORIO_APARC_ASEG / "aparc+aseg.mgz"), "-ot", "label", "-l", "freesurfercolorlut", "-o", "-w", "1"
        ]
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

    # -------------------------
    # Crear imagen de control de calidad
    # -------------------------
    crear_control_de_calidad(DIRECTORIO_MASCARAS)

    print("Todas las capturas se han generado exitosamente.")

def crear_control_de_calidad(DIRECTORIO_MASCARAS):
    imagen_1 = DIRECTORIO_MASCARAS / 'wm.png'
    imagen_2 = DIRECTORIO_MASCARAS / 'macroestructuras.png'
    imagen_3 = DIRECTORIO_MASCARAS / 'aseg.png'

    img1 = Image.open(imagen_1)
    img2 = Image.open(imagen_2)
    img3 = Image.open(imagen_3)

    width1, height1 = img1.size
    width2, height2 = img2.size
    width3, height3 = img3.size

    max_width = max(width1, width2, width3)
    img1 = img1.resize((max_width, height1), Image.LANCZOS)
    img2 = img2.resize((max_width, height2), Image.LANCZOS)
    img3 = img3.resize((max_width, height3), Image.LANCZOS)

    total_height = height1 + height2 + height3
    final_image = Image.new('RGB', (max_width, total_height))

    final_image.paste(img1, (0, 0))
    final_image.paste(img2, (0, height1))
    final_image.paste(img3, (0, height1 + height2))

    output_path = DIRECTORIO_MASCARAS / 'control_de_calidad.png'
    final_image.save(output_path)

    print(f'Imagen final guardada en {output_path}')