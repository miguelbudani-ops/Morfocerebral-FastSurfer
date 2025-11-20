# Morofometria Cerebral com FastSurfer

Pipeline reproducible de morfometría cerebral basada en **FastSurfer**, desarrollado en Instituto Balseiro / Fundación INTECNUS.

El objetivo principal es:

- Evaluar y comparar modelos de morfometría automática basados en **CNN** frente al flujo clásico de FreeSurfer.
- Implementar un **pipeline clínicamente utilizable**, desde DICOM hasta reportes morfométricos listos para interpretación, dentro de una arquitectura **contenedorizada con Docker**.

---

 **Selección y análisis de modelos** (`seleccion_modelos/`)  
   - Sección del proyecto destinada a la elección y prueba de modelos frente a FreeSurfer.
   - Cálculo de métricas de concordancia (por ejemplo, **Dice**, **HD95**).
   - Operaciones de posprocesado sobre volúmenes: normalización, resampling, etc.
   - Scripts para generar **gráficos de barras, cajas, volúmenes relativos**, etc.
   - Posible ejecución masiva en clúster / arrays de jobs.

## 1. Resumen del pipeline

A muy alto nivel, el flujo de trabajo que implementa este repositorio es:

1. **Entrada**  
   - Imágenes T1 cerebrales (DICOM) de sujetos sanos y/o pacientes.
   - Metadatos clínicos y de adquisición (institución local).

2. **Preprocesamiento** (`preprocessing/`)  
   - Organización de estudios por paciente.
   - Extracción de nombre / identificador de paciente desde DICOM.
   - Conversión a NIfTI 
   - Ejecución de **FastSurfer** y Sclimbic sobre los volúmenes T1.
   

3. **Procesamiento** (`processing/`)
   - Generación de superficies, etiquetas corticales y volúmenes subcorticales.
   - Exportación de métricas a formatos tabulares (CSV / XLSX).
   - Genración de graficos de poligonos y graficos temporales
   - Generación de reportes morfometricos

4. **Recursos auxiliares** (`recursos/`)  
   - Imágenes, plantillas y otros recursos que sirven de apoyo para informes y figuras de la tesis.

5. **Automatización y utilidades**  
   - `main_local.py`: punto de entrada para orquestar el pipeline en entorno local.
   - `extract_patient_name.py`: utilitario para leer el nombre del paciente desde directorios DICOM.
   - `send_email.py`: envío opcional de notificaciones por correo al finalizar trabajos.
   - `Dockerfile`: definición de la imagen que encapsula FreeSurfer, FastSurfer, FSL y dependencias. Esta imagen se crea considerando que existen en la carpeta que contiende el archivo Dockerfile, las carpetas de freesurfer y fastsurfer, no descarga los modelos desde dockerhub.
   - `morfometria_env.yml`: definición de entorno Conda para ejecución sin Docker.

---

## 2. Estructura del repositorio

```text
Morfocerebral-FastSurfer/
├── preprocessing/
│   └── ...           # Script de preprocesamiento lanza FastSrfer y ScLimbic(DICOM → NIfTI, organización, etc.)
├── processing/
│   └── ...           # Scripts de ejecución de fsl, freeview, creacion de graficas, reportes y manejo de salidas
├── recursos/
│   └── ...           # Imágenes, plantillas, recursos gráficos para informes
├── seleccion_modelos/
│   ├── calculo_dice.py
│   ├── calculo_hd95.py
│   ├── clinical.yml
│   ├── clinical_array_time.sh
│   ├── csvpromedio_vol.py
│   ├── fastsurfer_array.sh
│   ├── freesurfer_array.sh
│   ├── fs_resampled.py
│   ├── graficavolumenes.py
│   ├── graficavolumenes_rel.py
│   ├── grafico_de_barras.py
│   └── grafico_de_cajas.py
├── Dockerfile
├── extract_patient_name.py
├── main_local.py
├── morfometria_env.yml
└── send_email.py