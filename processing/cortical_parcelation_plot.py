import subprocess
import time
import cv2
import numpy as np
import os
from pathlib import Path
import sys

def capture_xvfb(display=":99", output_path=None, crop_coords=(310, None, 495, 703)):
    screenshot_cmd = f"xwd -root -display {display} | convert xwd:- png:-"
    capture_process = subprocess.Popen(screenshot_cmd, shell=True, stdout=subprocess.PIPE)
    img_array = np.asarray(bytearray(capture_process.stdout.read()), dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("La captura de pantalla no se pudo decodificar correctamente.")

    x_start, x_end, y_start, y_end = crop_coords
    x_end = x_end or img.shape[1]  # Si x_end es None, usar ancho total

    cropped_img = img[y_start:y_end, x_start:x_end]
    cv2.imwrite(str(output_path), cropped_img)
    print(f"Captura recortada guardada en: {output_path}")

def generate_parcelation_plot(dicom_dir, subjects_dir):
    # Paths
    DIRECTORIO_APARC_ASEG = Path(subjects_dir) / "mri"
    DIRECTORIO_T1 = Path(dicom_dir)
    nii_files = list(DIRECTORIO_T1.glob('*.nii'))

    if not nii_files:
        raise FileNotFoundError("No se encontró ningún archivo .nii en el directorio DICOM.")
    
    IMAGEN_T1 = nii_files[0]
    custom_lut_file = '/home/usuario/Bibliografia/pipeline_v2/recursos/aparc.DKTatlas+asegColorLUT.txt'

    # Archivos de salida
    output_screenshot_1 = DIRECTORIO_APARC_ASEG / 'parcelacion_cortical.png'
    output_screenshot_2 = DIRECTORIO_APARC_ASEG / 'sclimbic_3d.png'

    # Eliminar lock si existe
    lock_file = '/tmp/.X99-lock'
    if os.path.exists(lock_file):
        os.remove(lock_file)

    # Lanzar Xvfb
    xvfb_process = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1720x900x24"])
    time.sleep(20)

    env = dict(os.environ, DISPLAY=":99", GTK_IM_MODULE="none")
    openbox_process = subprocess.Popen(["openbox"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(20)

    # --------------------------
    # Primera ejecución: aparc.DKTatlas+aseg.mgz
    # --------------------------
    freeview_cmd_1 = [
        "freeview",
        "-v", f"{IMAGEN_T1}:opacity=0.9:smoothed=true",
        f"{DIRECTORIO_APARC_ASEG}/aparc.DKTatlas+aseg.mgz:colormap=lut:lut={custom_lut_file}",
        "-layout", "3",
        "-viewport", "3d",
        "-ras", "-8.30", "19.06", "62.15"
    ]

    freeview_proc_1 = subprocess.Popen(freeview_cmd_1, env=env)
    time.sleep(40)
    subprocess.run(['wmctrl', '-r', 'freeview', '-b', 'add,maximized_vert,maximized_horz'], env=env)
    time.sleep(20)
    subprocess.run(['xdotool', 'key', 'alt+1'], env=env)
    time.sleep(10)

    capture_xvfb(output_path=output_screenshot_1, crop_coords=(380, None, 495, 703))

    freeview_proc_1.terminate()
    freeview_proc_1.wait()

    # --------------------------
    # Segunda ejecución: sclimbic.mgz con isosuperficie
    # --------------------------
    freeview_cmd_2 = [
        "freeview",
        "-v", f"{IMAGEN_T1}:opacity=0.5:smoothed=true",
        f"{DIRECTORIO_APARC_ASEG}/sclimbic.mgz:isosurface=on",
        "-layout", "3",
        "-viewport", "3d",
        "-ras", "-8.30", "19.06", "62.15",
        "--hide-3d-frames"
    ]

    freeview_proc_2 = subprocess.Popen(freeview_cmd_2, env=env)
    time.sleep(40)
    subprocess.run(['wmctrl', '-r', 'freeview', '-b', 'add,maximized_vert,maximized_horz'], env=env)
    time.sleep(20)
    subprocess.run(['xdotool', 'key', 'alt+1'], env=env)
    time.sleep(10)

    capture_xvfb(output_path=output_screenshot_2, crop_coords=(380, 1700, 202, 410))  # Más arriba

    freeview_proc_2.terminate()
    freeview_proc_2.wait()

    # Cierre de entorno
    openbox_process.terminate()
    openbox_process.wait()
    xvfb_process.terminate()
    xvfb_process.wait()