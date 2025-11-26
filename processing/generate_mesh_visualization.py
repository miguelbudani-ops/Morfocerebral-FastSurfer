import subprocess
from pathlib import Path

def generate_mesh_visualization(dicom_dir, subjects_dir):
    # Definir rutas automáticamente
    DIRECTORIO_T1 = Path(dicom_dir)
    DIRECTORIO_FREESURFER = Path(subjects_dir)
    DIRECTORIO_MESH = DIRECTORIO_FREESURFER / "surf"
    DIRECTORIO_OUTPUT = DIRECTORIO_FREESURFER / "mri" / "mask"
    DIRECTORIO_OUTPUT.mkdir(parents=True, exist_ok=True)

    # Buscar el archivo .nii en el directorio T1
    nii_files = list(DIRECTORIO_T1.glob('*.nii'))
    if not nii_files:
        raise FileNotFoundError("No se encontró ningún archivo .nii en el directorio T1.")
    IMAGEN_T1 = nii_files[0]

    # Definir rutas de las mallas
    RH_WHITE = DIRECTORIO_MESH / "rh.white"
    LH_WHITE = DIRECTORIO_MESH / "lh.white"
    RH_PIAL = DIRECTORIO_MESH / "rh.pial"
    LH_PIAL = DIRECTORIO_MESH / "lh.pial"

    output_path = DIRECTORIO_OUTPUT / "mesh.png"

    # Comando FSLeyes render
    comando_render = [
        "fsleyes", "render",
        "-of", str(output_path),
        "--scene", "3d",
        "--size", "1600", "1200",
        "--zoom", "190",                         # acercar
        "--bgColour", "0", "0", "0",             # fondo negro
        "--hideCursor",                          # sin cursor
        "--hideLegend",                          # sin ejes de orientación
        "--performance", "3",                    # mejor calidad visual
        "--displaySpace", "world",
        "--offset", "-0.1", "-0.3",



        str(IMAGEN_T1), "-ot", "volume", "--alpha", "0",

        str(RH_WHITE), "-ot", "mesh", "--colour", "0.678", "0.847", "0.902", "--outline", "--outlineWidth", "1.3",
        str(LH_WHITE), "-ot", "mesh", "--colour", "0.0", "0.0", "0.0", "--outline", "--outlineWidth", "1.3",
        str(RH_PIAL),  "-ot", "mesh", "--colour", "0.0", "0.846", "1.0",   "--outline", "--outlineWidth", "1.3", "--wireframe",
        str(LH_PIAL),  "-ot", "mesh", "--colour", "0.898", "0.898", "0.898", "--outline", "--outlineWidth", "1.3", "--wireframe"
    ]


    print("Generando imagen 3D de mallas con fsleyes render...")
    subprocess.run(comando_render, check=True)
    print(f"Captura guardada en: {output_path}")