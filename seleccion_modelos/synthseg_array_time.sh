#!/bin/bash
#SBATCH --job-name=synthseg_array
#SBATCH --partition=multi
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-task=1
#SBATCH --cpus-per-task=10
#SBATCH --time=04:00:00
#SBATCH --output=/home/mbudani/results/synthseg_array_results_time/synthseg_%A_%a.out
#SBATCH --error=/home/mbudani/results/synthseg_array_results_time/synthseg_%A_%a.err
#SBATCH --array=1-15   # Ajusta al número de sujetos

set -euo pipefail

# ==============================
# CONFIGURACIÓN DEL USUARIO
# ==============================
INPUT_DIR="/home/mbudani/data/sujetos_prueba"                # Carpeta con subcarpetas de sujetos
OUTPUT_DIR="/home/mbudani/results/synthseg_array_results_time"  # Carpeta de salida general
SCRIPT_PATH="/home/mbudani/apps/SynthSeg/scripts/commands/SynthSeg_predict.py"
ENV_NAME="synthseg-gpu-cu12"

# ==============================
# ENTORNO
# ==============================
source /home/mbudani/miniconda3/etc/profile.d/conda.sh
conda activate "${ENV_NAME}"

# ==============================
# LISTA DE CARPETAS DE SUJETOS
# ==============================
mapfile -t SUBJECT_DIRS < <(find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

TOTAL_SUBJECTS=${#SUBJECT_DIRS[@]}
if (( TOTAL_SUBJECTS == 0 )); then
    echo "No se encontraron carpetas de sujetos en ${INPUT_DIR}"
    exit 1
fi

# Validar índice del array (1..N)
if (( SLURM_ARRAY_TASK_ID > TOTAL_SUBJECTS )); then
    echo "ERROR: SLURM_ARRAY_TASK_ID=$SLURM_ARRAY_TASK_ID excede el número de sujetos ($TOTAL_SUBJECTS)"
    exit 1
fi

# Seleccionar carpeta del sujeto
SUBJ_DIR="${SUBJECT_DIRS[$SLURM_ARRAY_TASK_ID-1]}"
SUBJ_NAME=$(basename "$SUBJ_DIR")

# ==============================
# DETECTAR ARCHIVO NII
# ==============================
T1_FILE=$(find "$SUBJ_DIR" -maxdepth 1 -type f \( -iname "*.nii" -o -iname "*.nii.gz" \) | head -n 1)

if [[ -z "$T1_FILE" ]]; then
    echo "ERROR: No se encontró archivo .nii en $SUBJ_DIR"
    exit 1
fi

echo "Procesando sujeto: $SUBJ_NAME"
echo "Archivo T1: $T1_FILE"

# ==============================
# CARPETA DE SALIDA POR SUJETO
# ==============================
SUBJECT_DIR="${OUTPUT_DIR}/${SUBJ_NAME}"
mkdir -p "${SUBJECT_DIR}"

OUT_SEG="${SUBJECT_DIR}/${SUBJ_NAME}_seg.nii.gz"
OUT_VOL="${SUBJECT_DIR}/volumes_${SUBJ_NAME}.csv"
OUT_QC="${SUBJECT_DIR}/qc_${SUBJ_NAME}.csv"

# ==============================
# SALTO SI YA EXISTE
# ==============================
if [[ -f "${OUT_SEG}" ]]; then
    echo "Segmentación ya existe: ${OUT_SEG} → salto"
    exit 0
fi

# --- Medición de tiempo ---
t_start=$(date +%s)
echo "Inicio: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"

# ==============================
# EJECUCIÓN DE SYNTHSEG
# ==============================
python "${SCRIPT_PATH}" --i "${T1_FILE}" --o "${OUT_SEG}" --parc --vol "${OUT_VOL}" --qc "${OUT_QC}"

echo "Finalizado sujeto: ${SUBJ_NAME}"

t_end=$(date +%s)
elapsed=$((t_end - t_start))
h=$((elapsed/3600)); m=$(( (elapsed%3600)/60 )); s=$((elapsed%60))
echo "Fin:    $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
printf "Duración: %02dh:%02dm:%02ds\n" $h $m $s
