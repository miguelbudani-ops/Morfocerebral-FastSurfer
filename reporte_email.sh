#!/usr/bin/env bash
# Ejecuta solo FSL y envía el correo. Solo requiere -p PACIENTE.
set -euo pipefail

# Constantes
OUTPUTS_ROOT="/mnt/data/Migue/outputs"
MENSAJE="/mnt/data/Migue/mensaje.txt"
DESTINATARIOS="/mnt/data/Migue/destinatarios.txt"
IMG="morfocerebral:full"

usage(){ echo "Uso: $(basename "$0") -p PACIENTE"; }

PACIENTE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--paciente) PACIENTE="${2:-}"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Flag desconocido: $1"; usage; exit 1;;
  esac
done
[[ -n "$PACIENTE" ]] || { echo "Falta -p/--paciente"; usage; exit 1; }
[[ -f "$MENSAJE" ]] || { echo "No existe MENSAJE: $MENSAJE"; exit 1; }
[[ -f "$DESTINATARIOS" ]] || { echo "No existe DESTINATARIOS: $DESTINATARIOS"; exit 1; }

PACIENTE_DIR="$OUTPUTS_ROOT/$PACIENTE"
DICOM_TOP="$PACIENTE_DIR/dicom"
[[ -d "$DICOM_TOP" ]] || { echo "No existe DICOM_DIR: $DICOM_TOP"; exit 1; }

# Buscar el directorio FastSurfer más reciente bajo dicom/
# Soporta múltiples niveles: .../dicom/**/FastSurfer/{mri,stats}
FS_DIR="$(find "$DICOM_TOP" -type d -name FastSurfer -printf '%T@ %p\n' | sort -nr | head -n1 | cut -d' ' -f2- || true)"
[[ -n "$FS_DIR" ]] || { echo "No se encontró carpeta FastSurfer dentro de $DICOM_TOP"; exit 2; }

# Validaciones clave
[[ -r "$FS_DIR/mri/aparc+aseg.mgz" ]] || { echo "Falta $FS_DIR/mri/aparc+aseg.mgz"; exit 3; }
[[ -d "$FS_DIR/stats" ]] || { echo "Falta carpeta stats en $FS_DIR"; exit 3; }

# Raíz DICOM real para posprocesamiento es el padre de FastSurfer
DICOM_ROOT="$(
  cd "$FS_DIR/.." >/dev/null
  pwd
)"

EMAIL_LOG="$PACIENTE_DIR/email_log.txt"

echo "Paciente: $PACIENTE"
echo "FastSurfer: $FS_DIR"
echo "DICOM_ROOT: $DICOM_ROOT"

# Construir ruta equivalente dentro del contenedor
# /data/paciente + (ruta relativa desde PACIENTE_DIR)
REL_CONT="${DICOM_ROOT#$PACIENTE_DIR}"
DICOM_ROOT_CONT="/data/paciente${REL_CONT}"

EDAD=$(docker run --rm \
            -v "$PACIENTE_DIR":/data/dicom:ro \
            "$IMG" bash -c '
                set -euo pipefail
                source /home/usuario/miniconda3/etc/profile.d/conda.sh &&
                conda activate morfometria_env >/dev/null 2>&1 &&
                python /home/usuario/Bibliografia/pipeline_v2/extract_patient_age.py /data/dicom')
echo "Edad del paciente $EDAD"

# Ejecutar FSL con la raíz correcta y saltando FS
docker run --rm \
  -v "$PACIENTE_DIR":/data/paciente:rw \
  "$IMG" bash -lc '
    set -e
    source /home/usuario/miniconda3/etc/profile.d/conda.sh
    conda activate morfometria_env
    echo "Usando --dicom_dir: '"$DICOM_ROOT_CONT"'"
    python3 /home/usuario/Bibliografia/pipeline_v2/main_local.py --skip_fs --dicom_dir '"$DICOM_ROOT_CONT"''

# Definir la ruta de los archivos PDF
  
  # Definir la ruta de los archivos PDF
  # Definir la ruta de los archivos PDF
  PDF_REPORTE_COMPLETO="$PACIENTE_DIR/dicom/FastSurfer/stats/Reporte_completo_comprimido.pdf"
  PDF_REPORTE_EPILEPSIA="$PACIENTE_DIR/dicom/FastSurfer/stats/Reporte_epilepsia_comprimido.pdf"
  PDF_REPORTE_MORF_ESP="$PACIENTE_DIR/dicom/FastSurfer/stats/Reporte_morf_esp_comprimido.pdf"
  PDF_REPORTE_PEDIATRICO="$PACIENTE_DIR/dicom/FastSurfer/stats/Reporte_pediatrico_comprimido.pdf"

  EDAD_NUM=${EDAD%% *}

    # Determinar los archivos a enviar
  if [[ "$EDAD_NUM" -lt 15 ]]; then
        # Si la edad es menor a 15, enviar los archivos pediátricos y completos
      ARCHIVOS_PDF=("$PDF_REPORTE_PEDIATRICO" "$PDF_REPORTE_COMPLETO")
  else
        # Si la edad es mayor o igual a 15, enviar los archivos completos, epilepsia y morfología
      ARCHIVOS_PDF=("$PDF_REPORTE_COMPLETO" "$PDF_REPORTE_EPILEPSIA" "$PDF_REPORTE_MORF_ESP")
  fi

  # Definir los destinatarios
  DESTINATARIOS_PATH="/mnt/data/Migue/destinatarios.txt"  # Ruta a los destinatarios (asegúrate de tenerlo configurado)
  MENSAJE_PATH="/mnt/data/Migue/mensaje.txt"  # Ruta al mensaje de correo

  # ----------------------------
  # Enviar el correo con los archivos seleccionados
  # ----------------------------
  EMAIL_LOG="$PACIENTE_DIR/email_log.txt"

  ADJUNTOS=()
  for pdf in "${ARCHIVOS_PDF[@]}"; do
      PDF_HOST="$PACIENTE_DIR/dicom/FastSurfer/stats/$(basename "$pdf")"
      [[ -f "$PDF_HOST" ]] || { echo "No existe $PDF_HOST, se omite" | tee -a "$EMAIL_LOG"; continue; }
      ADJUNTOS+=("/data/paciente/dicom/FastSurfer/stats/$(basename "$pdf")")
  done
  (( ${#ADJUNTOS[@]} )) || { echo "Sin PDFs válidos para enviar" | tee -a "$EMAIL_LOG"; return; }

  EMAIL_CMD=(
      python /home/usuario/Bibliografia/pipeline_v2/send_email.py
      "$PACIENTE"
      "/data/email/mensaje.txt"
      "/data/email/destinatarios.txt"
  )
  EMAIL_CMD+=("${ADJUNTOS[@]}")

  docker run --rm \
      -v "$PACIENTE_DIR":/data/paciente:ro \
      -v "$MENSAJE_PATH":/data/email/mensaje.txt:ro \
      -v "$DESTINATARIOS_PATH":/data/email/destinatarios.txt:ro \
      morfocerebral:full \
      bash -lc "set -e
          source /home/usuario/miniconda3/etc/profile.d/conda.sh
          conda activate morfometria_env
          $(printf '%q ' "${EMAIL_CMD[@]}")
      " >> "$EMAIL_LOG" 2>&1

  echo "Resultado del envío registrado en $EMAIL_LOG"