#!/bin/bash

# Script automatizado para procesar imágenes T1 para análisis morfométricos.
echo ""
echo "                                        888888888        "
echo "                                      88:::::::::88      "
echo "                                    88:::::::::::::88    "
echo "                                   8::::::88888:::::8    "
echo "              zzzzzzzzzzzzzzzzzz  8:::::8     8:::::8    "
echo "              z:::::::::::::::z   8:::::8     8:::::8    "
echo "              z::::::::::::::z    8:::::88888::::::8     "
echo "              zzzzzzzz::::::z      8:::::::::::::8       "
echo "                    z::::::z      8:::::88888:::::8      "
echo "                   z::::::z      8:::::8     8:::::8     "
echo "                  z::::::z      8:::::8      8:::::8     "
echo "                 z::::::z       8:::::8     8:::::8      "
echo "                z::::::zzzzzzzz 8::::::88888::::::8      "
echo "               z::::::::::::::z  88:::::::::::::88       "
echo "              z:::::::::::::::z    88:::::::::88         "
echo "             zzzzzzzzzzzzzzzzzz      888888888           "
echo ""
echo ""
echo "██╗███╗   ██╗████████╗███████╗ ██████╗███╗   ██╗██╗   ██╗███████╗"
echo "██║████╗  ██║╚══██╔══╝██╔════╝██╔════╝████╗  ██║██║   ██║██╔════╝"
echo "██║██╔██╗ ██║   ██║   █████╗  ██║     ██╔██╗ ██║██║   ██║███████╗"
echo "██║██║╚██╗██║   ██║   ██╔══╝  ██║     ██║╚██╗██║██║   ██║╚════██║"
echo "██║██║ ╚████║   ██║   ███████╗╚██████╗██║ ╚████║╚██████╔╝███████║"
echo "╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝"
echo "                                                                  "


# Función para mostrar ayuda
show_help() {
    echo "Este script procesa imágenes anatómicas T1 para obtener la segmentación y, posteriormente, la información morfológica en el espacio canónico del paciente."
    echo "Realiza las siguientes tareas:"
    echo "  1. Descomprime un archivo .zip (si corresponde)."
    echo "  2. Renombra archivos y carpetas para evitar espacios."
    echo "  3. Busca automáticamente el directorio con archivos DICOM."
    echo "  4. Convierte los archivos DICOM a formato NIfTI."
    echo "  5. Procesa las imágenes usando FreeSurfer (recon-all)."
    echo "  6. Realiza otra segmentación con una red neuronal convolucional en mri_synthseg."
    echo ""
    echo "Argumentos:"
    echo "  archivo.zip         Un archivo comprimido que contiene los datos del estudio."
    echo "  directorio          Un directorio raíz ya descomprimido con los datos del estudio."
    echo ""
    echo "Uso: $0 <archivo.zip o directorio>"
    echo ""
    echo "Ejemplo de uso:"
    echo "  $0 /ruta/al/archivo.zip"
    echo "  $0 /ruta/al/directorio"
    echo ""
    echo "Notas:"
    echo "  - FreeSurfer y dcm2niix deben estar instalados y disponibles en el PATH."
    echo "  - Los resultados de la segmentación y la información morfológica se guardarán en la carpeta 'FreeSurfer'."
    echo "  - Los resultados de mri_synthseg se guardarán en 'FreeSurfer/mri_synthseg'."
    echo ""
    exit 0
}

# Mostrar ayuda si no se pasa ningún argumento o si se usa la opción -h/--help
if [ "$#" -eq 0 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
fi

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
fi

if [ "$#" -ne 1 ]; then
    echo "Uso: $0 <archivo.zip o directorio>"
    exit 1
fi

INPUT="$1"

# Determinar si la entrada es un archivo .zip o un directorio
if [[ "$INPUT" == *.zip ]]; then
    if [ ! -f "$INPUT" ]; then
        echo "Error: el archivo $INPUT no existe."
        exit 1
    fi

    ZIP_DIR=$(dirname "$INPUT")
    echo "Descomprimiendo $INPUT en $ZIP_DIR..."
    unzip -o "$INPUT" -d "$ZIP_DIR" || { echo "Error al descomprimir $INPUT."; exit 1; }

    # Obtener el nombre original de la carpeta raíz
    ROOT_DIR=$(unzip -Z -1 "$INPUT" | head -1 | sed 's|/.*||')
    ROOT_DIR="$ZIP_DIR/$ROOT_DIR"

    # Renombrar la carpeta raíz si contiene espacios
    if [[ "$ROOT_DIR" == *" "* ]]; then
        RENAMED_ROOT_DIR="${ROOT_DIR// /_}"
        mv "$ROOT_DIR" "$RENAMED_ROOT_DIR"
        ROOT_DIR="$RENAMED_ROOT_DIR"
        echo "La carpeta raíz fue renombrada a: $ROOT_DIR"
    fi
else
    if [ ! -d "$INPUT" ]; then
        echo "Error: el directorio $INPUT no existe."
        exit 1
    fi
    ROOT_DIR="$INPUT"
fi

# Verificar si el directorio raíz existe
if [ ! -d "$ROOT_DIR" ]; then
    echo "Error: No se encontró el directorio raíz en $ROOT_DIR."
    exit 1
fi

# Renombrar subcarpetas y archivos dentro de la carpeta raíz
echo "Renombrando archivos y carpetas en $ROOT_DIR..."
python3 << EOF
import os
for root, dirs, files in os.walk("$ROOT_DIR", topdown=False):
    for name in dirs + files:
        old_path = os.path.join(root, name)
        new_name = name.replace(' ', '_')
        new_path = os.path.join(root, new_name)
        if old_path != new_path:
            os.rename(old_path, new_path)
EOF

# Paso 2: Buscar subcarpeta con archivos DICOM
DICOM_DIR=$(find "$ROOT_DIR" -type f -name "*.dcm" -exec dirname {} \; | head -1)
if [ -z "$DICOM_DIR" ]; then
    echo "Error: No se encontró un directorio con archivos DICOM en $ROOT_DIR."
    exit 1
fi

echo "Directorio de DICOM: $DICOM_DIR"

# Paso 3: Convertir DICOM a NIfTI
echo "Convirtiendo DICOM a NIfTI..."
dcm2niix -z n -f "%d" -o "$DICOM_DIR" "$DICOM_DIR" || { echo "Error al convertir DICOM a NIfTI."; exit 1; }

# Buscar el archivo NIfTI generado
NII_FILE=$(find "$DICOM_DIR" -maxdepth 1 -type f -name "*.nii")
if [ -z "$NII_FILE" ]; then
    echo "Error: No se generó un archivo NIfTI en $DICOM_DIR."
    exit 1
fi

echo "Archivo NIfTI generado: $NII_FILE"

# Paso 4: Configurar FreeSurfer
SUBJECTS_DIR="$DICOM_DIR"
export SUBJECTS_DIR
SUBJECT_NAME="FastSurfer"

LOG_DIR="$SUBJECTS_DIR/logs_fastsurfer"
mkdir -p "$LOG_DIR"

COMBINED_LOG="$LOG_DIR/log.txt"
exec > >(tee -a "$COMBINED_LOG") 2>&1

source "$FREESURFER_HOME/SetUpFreeSurfer.sh"
export FASTSURFER_HOME=/home/usuario/FastSurfer
source /home/usuario/miniconda3/etc/profile.d/conda.sh

conda activate fastsurfer

# Paso 5: Ejecutar FreeSurfer recon-all
if [ -f "$NII_FILE" ]; then
    echo "Ejecutando recon-all en modo paralelo..."
    echo "Usando archivo NIfTI: $NII_FILE"
    N_CORES=6  # Ajusta este valor según el número de núcleos disponibles

    "$FASTSURFER_HOME/run_fastsurfer.sh" --sid "$SUBJECT_NAME" --t1 "$NII_FILE" --sd "$SUBJECTS_DIR" --device cpu --fs_license "$FREESURFER_HOME/license.txt" --threads "$N_CORES" --vox_size 1.0 --allow_root
else
    echo "Error: El archivo NIfTI no existe o no se encuentra en $NII_FILE."
    exit 1
fi



# Paso 7: Ejecutar mri_sclimbic_seg para segmentar fornix y tubérculos mamilares
echo "Ejecutando mri_sclimbic_seg para $SUBJECT_NAME..."
mri_sclimbic_seg --s "$SUBJECT_NAME" --write_volumes --write_qa_stats
if [ $? -ne 0 ]; then
    echo "Error en mri_sclimbic_seg. Revisa $COMBINED_LOG para más detalles."
    exit 1
fi

conda deactivate 

echo ""
echo "Proceso completado exitosamente. Resultados disponibles en:"
echo "$SUBJECTS_DIR/$SUBJECT_NAME"
echo ""

# Conejito feliz
echo " (\(\ "
echo " ( ^.^)"
echo " o__(\")(\")"
echo ""
#echo ""
