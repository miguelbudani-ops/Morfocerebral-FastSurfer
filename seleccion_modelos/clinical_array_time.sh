#!/bin/bash
#SBATCH --job-name=clinical_array
#SBATCH --partition=multi
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=24:00:00
#SBATCH --array=1-15 # Sustituir N por el número de sujetos
#SBATCH --output=/home/mbudani/results/clinical_array_results_time/clinical_%x_%A_%a.out
#SBATCH --error=/home/mbudani/results/clinical_array_results_time/clinical_%x_%A_%a.err


# =========================
# 1) Activar entorno
# =========================
source /home/mbudani/miniconda3/etc/profile.d/conda.sh
conda activate freesurfer

# =========================
# 2) Configurar FreeSurfer
# =========================
export FREESURFER_HOME=/home/mbudani/apps/freesurfer
source $FREESURFER_HOME/SetUpFreeSurfer.sh
export PATH=$FREESURFER_HOME/bin:$PATH
export FSF_OUTPUT_FORMAT=nii.gz
export SUBJECTS_DIR=/home/mbudani/results/clinical_array_results_time
export MNI_DIR=/home/mbudani/apps/freesurfer/bin
export FSFAST_HOME=$FREESURFER_HOME/fsfast
# =========================
# 3) Definir directorios
# =========================
INPUT_DIR=/home/mbudani/data/sujetos_prueba

# Crear lista de carpetas de sujetos
mapfile -t SUBJECT_DIRS < <(find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

TOTAL_SUBJECTS=${#SUBJECT_DIRS[@]}

# Validar índice del array
if (( SLURM_ARRAY_TASK_ID > TOTAL_SUBJECTS )); then
    echo "ERROR: SLURM_ARRAY_TASK_ID=$SLURM_ARRAY_TASK_ID excede el número de sujetos ($TOTAL_SUBJECTS)"
    exit 1
fi

# Seleccionar carpeta del sujeto
SUBJ_DIR="${SUBJECT_DIRS[$SLURM_ARRAY_TASK_ID-1]}"
SUBJ_NAME=$(basename "$SUBJ_DIR")

# =========================
# 4) Detectar archivo T1
# =========================
T1_FILE=$(find "$SUBJ_DIR" -maxdepth 1 -type f \( -iname "*.nii" -o -iname "*.nii.gz" \) | head -n 1)

if [[ -z "$T1_FILE" ]]; then
    echo "ERROR: No se encontró archivo T1 en $SUBJ_DIR"
    exit 1
fi

echo "Procesando sujeto: $SUBJ_NAME"
echo "Archivo T1: $T1_FILE"

# --- Medición de tiempo ---
t_start=$(date +%s)
echo "Inicio: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"

# 3) Ejecución del pipeline clínico
recon-all-clinical.sh "$T1_FILE" "$SUBJ_NAME" 10

# --- Cálculo de duración ---
t_end=$(date +%s)
elapsed=$((t_end - t_start))
h=$((elapsed/3600)); m=$(( (elapsed%3600)/60 )); s=$((elapsed%60))
echo "Fin:    $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
printf "Duración: %02dh:%02dm:%02ds\n" $h $m $s

