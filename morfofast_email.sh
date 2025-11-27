#!/usr/bin/env bash
# Procesamiento morfométrico con una sola imagen Docker (morfocerebral:full)

set -euo pipefail

# Matar ejecuciones previas de parallel (si quedaban colgadas)
pkill -f "parallel -j 2 --line-buffer procesar_paciente" || true

# -------------------------
# Configuración
# -------------------------
IMAGE_NAME="${IMAGE_NAME:-morfocerebral:full}"

WATCH_DIR="${WATCH_DIR:-/home/nz8/volu_morfo/data/inputs}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/home/nz8/volu_morfo/data/outputs}"
QUEUE_FILE="${QUEUE_FILE:-/tmp/job_queue/files_to_process_fast.txt}"

mkdir -p "$(dirname "$QUEUE_FILE")" "$OUTPUT_ROOT"
: > "$QUEUE_FILE"

wait_until_complete() {
  local file="$1"
  echo "Esperando a que $file finalice escritura..."
  local prev_size=0 size=0
  while true; do
    sleep 5
    size=$(stat -c%s "$file" 2>/dev/null || echo 0)
    if [[ "$size" -eq "$prev_size" ]]; then
      break
    fi
    prev_size=$size
  done
  echo "Archivo estable: $file"
}


procesar_paciente() {
    local FILE="$1"
    echo "Procesando archivo: $FILE"

    if [[ -f "$FILE" && "$FILE" == *.zip ]]; then
        wait_until_complete "$FILE"
        echo "Archivo ZIP detectado."

        TMP_UNZIP_DIR="${FILE%.zip}_temp"
        unzip -o "$FILE" -d "$TMP_UNZIP_DIR"
        DICOM_DIR=$(find "$TMP_UNZIP_DIR" -type f -name "*.dcm" -exec dirname {} \; | head -n 1)

        echo "DICOM_DIR DETECTADO: $DICOM_DIR"

        NOMBRE_PACIENTE=$(docker run --rm \
            -v "$DICOM_DIR":/data/dicom:ro \
            morfocerebral:full bash -c '
                set -euo pipefail
                source /home/usuario/miniconda3/etc/profile.d/conda.sh &&
                conda activate morfometria_env >/dev/null 2>&1 &&
                python /home/usuario/Bibliografia/pipeline_v2/extract_patient_name.py /data/dicom')
        
        echo "NOMBRE_PACIENTE: $NOMBRE_PACIENTE"

        EDAD=$(docker run --rm \
            -v "$DICOM_DIR":/data/dicom:ro \
            morfocerebral:full bash -c '
                set -euo pipefail 
                source /home/usuario/miniconda3/etc/profile.d/conda.sh &&
                conda activate morfometria_env >/dev/null 2>&1 &&
                python /home/usuario/Bibliografia/pipeline_v2/extract_patient_age.py /data/dicom')

        PACIENTE_DIR="$OUTPUT_ROOT/$NOMBRE_PACIENTE"
        mkdir -p "$PACIENTE_DIR/dicom"
        cp -r "$TMP_UNZIP_DIR"/* "$PACIENTE_DIR/dicom/"
        rm -rf "$TMP_UNZIP_DIR"

    elif [[ -d "$FILE" ]]; then
        echo "Directorio DICOM detectado."
        DICOM_DIR="$FILE"
        if find "$DICOM_DIR" -type d -name "FastSurfer" | grep -q .; then
            echo "Ya contiene resultados de FastSurfer. Ignorando."
            return
        fi

        NOMBRE_PACIENTE=$(docker run --rm \
            -v "$DICOM_DIR":/data/dicom:ro \
            morfocerebral:full bash -c '
                set -euo pipefail
                source /home/usuario/miniconda3/etc/profile.d/conda.sh &&
                conda activate morfometria_env >/dev/null 2>&1 &&
                python /home/usuario/Bibliografia/pipeline_v2/extract_patient_name.py /data/dicom')
        
        echo "NOMBRE_PACIENTE: $NOMBRE_PACIENTE"

        EDAD=$(docker run --rm \
            -v "$DICOM_DIR":/data/dicom:ro \
            morfocerebral:full bash -c '
                set -euo pipefail
                source /home/usuario/miniconda3/etc/profile.d/conda.sh &&
                conda activate morfometria_env >/dev/null 2>&1 &&
                python /home/usuario/Bibliografia/pipeline_v2/extract_patient_age.py /data/dicom')

        PACIENTE_DIR="$OUTPUT_ROOT/$NOMBRE_PACIENTE"
        mkdir -p "$PACIENTE_DIR/dicom"
        cp -r "$DICOM_DIR"/* "$PACIENTE_DIR/dicom/"
    else
        echo "Formato no reconocido. Ignorando."
        return
    fi

    echo "Esperando 10 segundos antes de iniciar el procesamiento..."
    sleep 10

    CONTAINER_NAME="fs_paciente_${NOMBRE_PACIENTE//[^a-zA-Z0-9]/}$(date +%s%N)"
    LOG_PATH="$PACIENTE_DIR/freesurfer_log.txt"

    echo "Iniciando procesamiento en contenedor: $CONTAINER_NAME"
    docker run -d --name "$CONTAINER_NAME" \
    -v "$PACIENTE_DIR":/data/paciente:rw \
    "$IMAGE_NAME" \
    bash -lc '
      set -euo pipefail
      source /home/usuario/miniconda3/etc/profile.d/conda.sh
      conda activate morfometria_env
      /usr/local/bin/start_xvfb.sh || true
      # Wrapper del pipeline que debe realizar TODO (FS + FSL + reportes)
      python /home/usuario/Bibliografia/pipeline_v2/main_local.py "/data/paciente/dicom"
    '

    echo "Esperando a que finalice el contenedor $CONTAINER_NAME..."
    docker wait "$CONTAINER_NAME" >/dev/null

    docker logs "$CONTAINER_NAME" >> "$LOG_PATH" 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null || true

    echo "Pipeline completado para $NOMBRE_PACIENTE"

    # (Opcional) Descubrir carpeta FastSurfer y verificar reporte
    FS_DIR="$(find "$PACIENTE_DIR/dicom" -type d -name FastSurfer -printf "%T@ %p\n" | sort -nr | head -n1 | cut -d" " -f2- || true)"
    if [[ -n "${FS_DIR:-}" ]]; then
        PDF_REPORTE="$FS_DIR/stats/Reporte_morf.pdf"
        if [[ -f "$PDF_REPORTE" ]]; then
            echo "Reporte generado: $PDF_REPORTE"
        else
            echo "Reporte no encontrado bajo: $FS_DIR/stats"
        fi
    fi


  
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
      "$NOMBRE_PACIENTE"
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

}




export -f wait_until_complete  procesar_paciente
export IMAGE_NAME OUTPUT_ROOT

# Lector de cola -> parallel
tail -n +1 -f "$QUEUE_FILE" | parallel -j 2 --line-buffer procesar_paciente {} &

# Watcher de entrada -> encola trabajos
inotifywait -m -e close_write,moved_to --format '%w%f' "$WATCH_DIR" | while read -r NEWFILE; do
  BASENAME=$(basename "$NEWFILE")
  if [[ "$BASENAME" == _temp || "$BASENAME" == . || "$BASENAME" == *~ ]]; then
    echo "Ignorado archivo temporal o incompleto: $NEWFILE"
    continue
  fi
  echo "Detectado nuevo archivo finalizado: $NEWFILE"
  grep -Fxq "$NEWFILE" "$QUEUE_FILE" || echo "$NEWFILE" >> "$QUEUE_FILE"
done