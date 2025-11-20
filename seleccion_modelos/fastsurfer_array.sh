#!/bin/bash
#SBATCH --job-name=fastsurfer_array
#SBATCH --partition=multi
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-task=1
#SBATCH --cpus-per-task=10
#SBATCH --time=24:00:00
#SBATCH --array=1-10   # N se sustituye automáticamente más abajo si quieres
#SBATCH --output=/home/mbudani/results/fastsurfer_array_results_2021/%x_%A_%a.out
#SBATCH --error=/home/mbudani/results/fastsurfer_array_results_2021/%x_%A_%a.err

# =========================
# CONFIGURACIÓN DEL ENTORNO
# =========================
source /home/mbudani/miniconda3/etc/profile.d/conda.sh
conda activate fastsurfer-gpu

export FREESURFER_HOME=/home/mbudani/apps/freesurfer
source $FREESURFER_HOME/SetUpFreeSurfer.sh
export PATH=$FREESURFER_HOME/bin:$PATH
export FSF_OUTPUT_FORMAT=nii.gz
export SUBJECTS_DIR=/home/mbudani/results/freesurfer_results
export MNI_DIR=$FREESURFER_HOME/mni
export FSFAST_HOME=$FREESURFER_HOME/fsfast
export FASTSURFER_HOME=$HOME/apps/FastSurfer

# =========================
# LISTA DE SUJETOS
# =========================
INPUT_DIR=/home/mbudani/data/data_2021
OUTPUT_DIR=/home/mbudani/results/fastsurfer_array_results_2021

# Crear lista de carpetas de sujetos (ordenadas)
mapfile -t SUBJECT_DIRS < <(find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

TOTAL_SUBJECTS=${#SUBJECT_DIRS[@]}

# Validar índice del array
if (( SLURM_ARRAY_TASK_ID > TOTAL_SUBJECTS )); then
    echo "ERROR: SLURM_ARRAY_TASK_ID=$SLURM_ARRAY_TASK_ID excede el número de sujetos ($TOTAL_SUBJECTS)"
    exit 1
fi

# Seleccionar sujeto correspondiente a este job
SUBJ_DIR="${SUBJECT_DIRS[$SLURM_ARRAY_TASK_ID-1]}"
SUBJ_NAME=$(basename "$SUBJ_DIR")

# =========================
# DETECTAR ARCHIVO T1
# =========================
T1_FILE=$(find "$SUBJ_DIR" -maxdepth 1 -type f \( -iname "*.mgz" -o -iname "*.nii.gz" \) | head -n 1)

if [[ -z "$T1_FILE" ]]; then
    echo "ERROR: No se encontró archivo T1 en $SUBJ_DIR"
    exit 1
fi

echo "Procesando sujeto: $SUBJ_NAME"
echo "Archivo T1: $T1_FILE"

# =========================
# EJECUTAR FASTSURFER
# =========================
$FASTSURFER_HOME/run_fastsurfer.sh \
    --t1 "$T1_FILE" \
    --fs_license "$FREESURFER_HOME/license.txt" \
    --sd "$OUTPUT_DIR" \
    --sid "$SUBJ_NAME" \
    --threads 10 \
    --device cuda
