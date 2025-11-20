import os
import nibabel as nib
import numpy as np
from pathlib import Path

def generate_brain_masks(subjects_dir):
    """
    Genera máscaras para los hemisferios, cerebelo, tallo cerebral y cuerpo calloso 
    a partir del archivo 'aparc+aseg.mgz' de FreeSurfer.

    Parameters:
    subjects_dir (str): Ruta al directorio 'FreeSurfer' donde se encuentra la carpeta 'mri'.
    """

    # Ruta del directorio 'mri' y subcarpeta 'mask'
    DIRECTORIO_APARC_ASEG = Path(subjects_dir) / "mri"
    dir_masks = os.path.join(DIRECTORIO_APARC_ASEG, 'mask')

    # Cargar el archivo 'aparc+aseg.mgz' de FreeSurfer
    archivo = os.path.join(DIRECTORIO_APARC_ASEG, 'aparc+aseg.mgz')
    img = nib.load(archivo)
    data = img.get_fdata()

    # Cargar el archivo 'sclimbic.mgz' 
    archivolimbic = os.path.join(DIRECTORIO_APARC_ASEG, 'sclimbic.mgz')
    imglimbic = nib.load(archivolimbic)
    data_limbic = imglimbic.get_fdata()

    # Etiquetas para las estructuras anatómicas
    etiquetas_gris_izquierdo = list(range(1000, 1036)) + list(range(3000, 3036))
    etiquetas_gris_derecho = list(range(2000, 2036)) + list(range(4000, 4036))
    etiquetas_blanca_izquierdo = [2, 10, 11, 12, 13, 17, 18, 26, 28]
    etiquetas_blanca_derecho = [41, 49, 50, 51, 52, 53, 54, 58, 60]
    etiquetas_cerebelo = [8, 47, 7, 46]
    etiquetas_brain_stem = 16
    etiquetas_cuerpo_calloso = [251, 252, 253, 254, 255]

    #etiquetas de estructuras lobulares (para informes especificos)
    lobulo_temporal=[1006,2006,1007,2007,1009,2009,1015,2015,2016,1016,1030,2030,2034,1034]
    lobulo_frontal=[1003,2003,1012,2012,1014,2014,1017,2017,1018,2018,1019,2019,1020,2020,1024,2024,1027,2027,1028,2028]
    lobulo_parietal=[1008,2008,1022,2022,1025,2025,2029,1029,1031,2031]
    lobulo_occipital=[1005,2005,1011,2011,1013,2013,1021,2021]

    #etiquetas de estructuras para informes especificos
    amigdala=[18,54]
    talamo=[10,49]
    Ventriculos_laterales=[4,43]
    ganglios_basales=[11,50,12,51,26,58]


    #etiquetas de estructuras limbicas para informe de epilepsia
    Hipocampo=[17,53]
    fornix=[821,822]
    Cuerpos_mamilares=[843,844]

    # Unir etiquetas para hemisferios
    etiquetas_hemisferio_izquierdo = etiquetas_gris_izquierdo + etiquetas_blanca_izquierdo
    etiquetas_hemisferio_derecho = etiquetas_gris_derecho + etiquetas_blanca_derecho

    # Crear máscaras para cada estructura
    mask_izquierdo = np.isin(data, etiquetas_hemisferio_izquierdo)
    mask_derecho = np.isin(data, etiquetas_hemisferio_derecho)
    mask_cerebelo = np.isin(data, etiquetas_cerebelo)
    mask_brain_stem = np.isin(data, etiquetas_brain_stem)
    mask_cuerpo_calloso = np.isin(data, etiquetas_cuerpo_calloso)


    # Crear mascaras para lobulos frontales 
    mask_lobulo_temporal = np.isin(data, lobulo_temporal)
    mask_lobulo_frontal = np.isin(data, lobulo_frontal)
    mask_lobulo_parietal = np.isin(data, lobulo_parietal)
    mask_lobulo_occipital = np.isin(data, lobulo_occipital)

    # Mascaras de estructuras para informes especificos
    mask_amigdala=np.isin(data, amigdala)
    mask_talamo=np.isin(data, talamo)
    mask_ventriculos_laterales=np.isin(data, Ventriculos_laterales)
    mask_ganglios_basales=np.isin(data, ganglios_basales)

    # Mascaras de estructuras limbicas para informe de epilepsia
    mask_hipocampo=np.isin(data, Hipocampo)
    mask_fornix=np.isin(data_limbic, fornix)
    mask_cuerpos_mamilares=np.isin(data_limbic, Cuerpos_mamilares)

    # Crear el directorio 'mask' si no existe
    os.makedirs(dir_masks, exist_ok=True)

    # Guardar las máscaras como nuevas imágenes NIFTI
    nib.save(nib.Nifti1Image(mask_izquierdo.astype(np.uint8), img.affine), f'{dir_masks}/mask_hemisferio_izquierdo.nii')
    print("✔ Máscara de hemisferio izquierdo guardada.")

    nib.save(nib.Nifti1Image(mask_derecho.astype(np.uint8), img.affine), f'{dir_masks}/mask_hemisferio_derecho.nii')
    print("✔ Máscara de hemisferio derecho guardada.")

    nib.save(nib.Nifti1Image(mask_cerebelo.astype(np.uint8), img.affine), f'{dir_masks}/mask_cerebelo.nii')
    print("✔ Máscara de cerebelo guardada.")

    nib.save(nib.Nifti1Image(mask_brain_stem.astype(np.uint8), img.affine), f'{dir_masks}/mask_brain_stem.nii')
    print("✔ Máscara de tallo cerebral guardada.")

    nib.save(nib.Nifti1Image(mask_cuerpo_calloso.astype(np.uint8), img.affine), f'{dir_masks}/mask_cuerpo_calloso.nii')
    print("✔ Máscara de cuerpo calloso guardada.")


    # Guardar las máscaras de lóbulos temporales como nuevas imágenes NIFTI
    nib.save(nib.Nifti1Image(mask_lobulo_temporal.astype(np.uint8), img.affine), f'{dir_masks}/mask_lobulo_temporal.nii')
    print("✔ Máscara de lóbulo temporal guardada.")

    nib.save(nib.Nifti1Image(mask_lobulo_frontal.astype(np.uint8), img.affine), f'{dir_masks}/mask_lobulo_frontal.nii')
    print("✔ Máscara de lóbulo frontal guardada.") 

    nib.save(nib.Nifti1Image(mask_lobulo_parietal.astype(np.uint8), img.affine), f'{dir_masks}/mask_lobulo_parietal.nii')
    print("✔ Máscara de lóbulo parietal guardada.")

    nib.save(nib.Nifti1Image(mask_lobulo_occipital.astype(np.uint8), img.affine), f'{dir_masks}/mask_lobulo_occipital.nii')
    print("✔ Máscara de lóbulo occipital guardada.")


    # Guardar las máscaras de estructuras para informes especificos
    nib.save(nib.Nifti1Image(mask_amigdala.astype(np.uint8), img.affine), f'{dir_masks}/mask_amigdala.nii')
    print("✔ Máscara de amígdala guardada.")       

    nib.save(nib.Nifti1Image(mask_talamo.astype(np.uint8), img.affine), f'{dir_masks}/mask_talamo.nii')
    print("✔ Máscara de tálamo guardada.")

    nib.save(nib.Nifti1Image(mask_ventriculos_laterales.astype(np.uint8), img.affine), f'{dir_masks}/mask_ventriculos_laterales.nii')
    print("✔ Máscara de ventrículos laterales guardada.")

    nib.save(nib.Nifti1Image(mask_ganglios_basales.astype(np.uint8), img.affine), f'{dir_masks}/mask_ganglios_basales.nii')
    print("✔ Máscara de ganglios basales guardada.")

    #guardar las máscaras de estructuras limbicas para informe de epilepsia
    nib.save(nib.Nifti1Image(mask_hipocampo.astype(np.uint8), img.affine), f'{dir_masks}/mask_hipocampo.nii')
    print("✔ Máscara de hipocampo guardada.")
    nib.save(nib.Nifti1Image(mask_fornix.astype(np.uint8), img.affine), f'{dir_masks}/mask_fornix.nii')
    print("✔ Máscara de fornix guardada.")
    nib.save(nib.Nifti1Image(mask_cuerpos_mamilares.astype(np.uint8), img.affine), f'{dir_masks}/mask_cuerpos_mamilares.nii')
    print("✔ Máscara de cuerpos mamilares guardada.")

    print("Todas las máscaras se han generado y guardado exitosamente.")