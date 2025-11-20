import subprocess
from pathlib import Path
from PIL import Image  # Importamos la librería Pillow
import sys # Para manejo de errores

def generate_lobes_visualization(subjects_dir):
    # --- 1. Definir Rutas ---
    DIRECTORIO_FREESURFER = Path(subjects_dir)
    DIRECTORIO_MASK = DIRECTORIO_FREESURFER / "mri" / "mask"
    DIRECTORIO_OUTPUT = DIRECTORIO_FREESURFER / "mri" / "mask"
    DIRECTORIO_OUTPUT.mkdir(parents=True, exist_ok=True)

    # Rutas de las máscaras
    try:
        FRONTAL = next(DIRECTORIO_MASK.glob("mask_lobulo_frontal.nii*"))
        TEMPORAL = next(DIRECTORIO_MASK.glob("mask_lobulo_temporal.nii*"))
        OCCIPITAL = next(DIRECTORIO_MASK.glob("mask_lobulo_occipital.nii*"))
        PARIETAL = next(DIRECTORIO_MASK.glob("mask_lobulo_parietal.nii*"))
    except StopIteration as e:
        print(f"Error: No se pudo encontrar uno de los archivos de máscara en {DIRECTORIO_MASK}", file=sys.stderr)
        print("Asegúrate de que los archivos 'mask_temporal', 'mask_frontal', etc. existan.", file=sys.stderr)
        print(f"Detalle del error: {e}", file=sys.stderr)
        return

    # Rutas de salida
    final_output_path = DIRECTORIO_OUTPUT / "lobulos_vistas_combinadas.png"
    temp_sag_path = DIRECTORIO_OUTPUT / "_temp_sag.png"
    temp_cor_path = DIRECTORIO_OUTPUT / "_temp_cor.png"
    temp_ax_path = DIRECTORIO_OUTPUT / "_temp_ax.png"
    temp_paths = [temp_sag_path, temp_cor_path, temp_ax_path]

    # --- 2. Argumentos de FSLeyes ---

    # Argumentos comunes de la escena
    base_scene_args = [
        "--scene", "3d",
        "--worldLoc", "6.681396", "21.5", "-20.009902", 
        "--displaySpace", "world",
        "--zoom", "173.5", # Es posible que quieras ajustar esto
        "--lightPos", "0.0", "0.0", "0.0",
        "--lightDistance", "2.0",
        "--offset", "0.164086", "-0.217522", 
        "--bgColour", "1.0", "1.0", "1.0", # Fondo blanco como en tu imagen
        "--fgColour", "0.0", "0.0", "0.0",
        #"--cursorColour", "0.0", "1.0", "0.0", 
        "--performance", "3",
        "--hideCursor", # Ocultamos la cruz verde
        "--hideLegend",
    ]

    # Argumentos de los archivos (estos son los mismos para cada render)
    file_args = [
        str(FRONTAL), 
        "-n", "mask_frontal", "-ot", "volume", "-a", "100.0", "-b", "49.75", 
        "-c", "49.90", "-cm", "red", "-nc", "greyscale", "-dr", "0.0", "1.01", 
        "-cr", "0.0", "1.01", "-cmr", "256", "-in", "spline", "-ns", "150", 
        "-r", "100", "-v", "0",

        str(PARIETAL), 
        "-n", "mask_parietal", "-ot", "volume", "-a", "100.0", "-b", "49.75", 
        "-c", "49.90", "-cm", "blue", "-nc", "greyscale", "-dr", "0.0", "1.01", 
        "-cr", "0.0", "1.01", "-cmr", "256", "-in", "spline", "-ns", "150", 
        "-r", "100", "-v", "0",

        str(OCCIPITAL), 
        "-n", "mask_occipital", "-ot", "volume", "-a", "100.0", "-b", "49.75", 
        "-c", "49.90", "-cm", "red-yellow", "-nc", "greyscale", "-dr", "0.0", "1.01", 
        "-cr", "0.0", "1.01", "-cmr", "256", "-in", "spline", "-ns", "150", 
        "-r", "100", "-v", "0",
        
        str(TEMPORAL), 
        "-n", "mask_temporal", "-ot", "volume", "-a", "100.0", "-b", "49.75", 
        "-c", "49.90", "-cm", "green", "-nc", "greyscale", "-dr", "0.0", "1.01", 
        "-cr", "0.0", "1.01", "-cmr", "256", "-in", "spline", "-ns", "150", 
        "-r", "100", "-v", "0",
    ]

   # Vistas a renderizar: (archivo_salida, argumentos_camara)
    # FIX: Reordenadas para coincidir con tu imagen (Axial, Coronal, Sagital)
    views = [
        (temp_ax_path, ["--cameraRotation", "90", "0", "0"]),   # Vista Axial (superior)
        (temp_cor_path, ["--cameraRotation", "180", "0", "0"]), # Vista Coronal (trasera)
        (temp_sag_path, ["--cameraRotation", "90", "0", "90"])  # Vista Sagital
    ]

    # --- 3. Generar las 3 imágenes ---
    print("Generando 3 vistas individuales con fsleyes render...")
    for output_file, camera_args in views:
        print(f"Renderizando {output_file.name}...")
        comando_render = (
            ["fsleyes", "render", "-of", str(output_file)] +
            base_scene_args +
            camera_args +
            file_args
        )
        # print(" ".join(comando_render)) # Descomenta para depurar el comando
        subprocess.run(comando_render, check=True)
    
    print("Vistas generadas.")

    # --- 4. Combinar las imágenes ---
    print("Combinando imágenes con Pillow...")
    try:
        # FIX: Cargar imágenes en el orden correcto
        images = [Image.open(p) for p in [temp_ax_path, temp_cor_path, temp_sag_path]]
        
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths)
        max_height = max(heights)
        
        combined_image = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        
        x_offset = 0
        for im in images:
            # --- ¡ESTA ES LA LÓGICA CORREGIDA! ---
            # Calcular el desfase vertical (y) para centrar la imagen
            y_offset = (max_height - im.height) // 2
            
            # Pegar la imagen usando el 'x_offset' y el 'y_offset' calculado
            combined_image.paste(im, (x_offset, y_offset))
            # ------------------------------------
            
            x_offset += im.width
            im.close() 

        combined_image.save(final_output_path)
        print(f"¡Imagen combinada guardada en: {final_output_path}!")

    except Exception as e:
        print(f"Error al combinar las imágenes: {e}", file=sys.stderr)

    # --- 5. Limpiar archivos temporales ---
    print("Limpiando archivos temporales...")
    for p in temp_paths:
        try:
            p.unlink()
        except OSError as e:
            print(f"No se pudo eliminar {p}: {e}", file=sys.stderr)