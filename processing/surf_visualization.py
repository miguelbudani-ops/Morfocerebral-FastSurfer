import os
import nibabel as nib
import numpy as np
from nilearn import plotting
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import cv2

def visualizar_espesores(freesurfer_dir):
    """
    Carga la superficie cortical y los datos de grosor desde FreeSurfer,
    genera un HTML interactivo y captura imágenes con los mismos parámetros del HTML.

    Parámetros:
    - freesurfer_dir: Ruta a la carpeta FreeSurfer del paciente.

    Guarda:
    - HTML interactivo de la visualización 3D en surf/visualizacion_espesores.html
    - Imágenes de cortes sagital, coronal y axial en surf/ (solo las recortadas)
    """

    # Rutas de los archivos combinados
    combined_pial_path = os.path.join(freesurfer_dir, 'surf', 'combined.pial')
    combined_thickness_path = os.path.join(freesurfer_dir, 'surf', 'combined.thickness')

    if not os.path.exists(combined_pial_path) or not os.path.exists(combined_thickness_path):
        print("No se encontraron los archivos combinados de superficie y grosor.")
        return

    print("Cargando datos de superficie y grosor cortical para visualización...")

    # Cargar geometría y grosor cortical
    combined_pial_data = nib.freesurfer.io.read_geometry(combined_pial_path)
    combined_pial_coords = combined_pial_data[0]  # Coordenadas
    combined_pial_faces = combined_pial_data[1]  # Caras
    combined_thickness = nib.freesurfer.io.read_morph_data(combined_thickness_path)

    # Calcular los valores mínimo y máximo de grosor cortical
    min_thickness = np.min(combined_thickness)
    max_thickness = np.max(combined_thickness)

    print(f"Rango de datos de espesor cortical: min={min_thickness:.2f}, max={max_thickness:.2f}")

    # Generar visualización interactiva en HTML
    html_output_path = os.path.join(freesurfer_dir, 'surf', 'visualizacion_espesores.html')
    view_combined_files = plotting.view_surf(
        (combined_pial_coords, combined_pial_faces),
        combined_thickness,
        cmap='jet',
        threshold=0.1,
        vmin=min_thickness,
        vmax=max_thickness,
        symmetric_cmap=False,
        title=''
    )
    view_combined_files.save_as_html(html_output_path)
    print(f"Visualización interactiva guardada en: {html_output_path}")

    # Configuración de Selenium para capturar imágenes
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ejecutar sin interfaz gráfica
    chrome_options.add_argument("--window-size=1200x1000")
    #chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Inicializar el navegador
    driver = webdriver.Chrome(options=chrome_options)

    # Abrir el archivo HTML generado
    driver.get(f"file://{html_output_path}")

    # Esperar a que se cargue el contenido completamente
    driver.implicitly_wait(6)

    # Definir rutas de salida
    img_output_dir = os.path.join(freesurfer_dir, 'surf')
    os.makedirs(img_output_dir, exist_ok=True)

    # 📌 *Mapeo de vistas del dropdown en HTML*
    views = {
        "ax_thickness.png": "top",  # Vista axial (superior)
        "cor_thickness.png": "front",  # Vista coronal (frontal)
        "sag_thickness.png": "right",  # Vista sagital (derecha)
    }

    try:
        # Buscar el menú desplegable de vistas
        select_element = driver.find_element(By.ID, "select-view")
        select = Select(select_element)
    except Exception as e:
        print(f"Error: No se encontró el selector de vista en el HTML. {e}")
        driver.quit()
        return

    for filename, view in views.items():
        output_path = os.path.join(img_output_dir, filename)

        try:
            # Seleccionar la vista deseada
            select.select_by_value(view)
            print(f"Vista cambiada a {view}")

            # Esperar 6 segundos para que la vista se actualice
            driver.implicitly_wait(6)

            # Capturar la imagen de la vista seleccionada
            driver.save_screenshot(output_path)
            print(f"Imagen guardada en: {output_path}")

            #Recortar la imagen con OpenCV
            img = cv2.imread(output_path)
            if img is not None:
                # Ajusta los valores de recorte según la captura
                x_start, x_end = 60, 430
                y_start, y_end = 28, 345
                cropped_img = img[y_start:y_end, x_start:x_end]

                # Guardar solo la imagen recortada (sobrescribiendo la original)
                cv2.imwrite(output_path, cropped_img)
                print(f"Imagen guardada en: {output_path}")
            else:
                print(f"Error: No se pudo cargar la imagen en {output_path}")

        except Exception as e:
            print(f"Error cambiando a vista {view}: {e}")

    # Cerrar el navegador
    driver.quit()
    print("Captura de imágenes finalizada.")