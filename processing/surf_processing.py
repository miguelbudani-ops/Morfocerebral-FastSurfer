import numpy as np
import nibabel as nib
import os


def procesar_superficie_y_grosor(freesurfer_dir):
    """
    Carga y combina datos de superficie y grosor cortical de ambos hemisferios cerebrales.
    
    Parámetros:
    - freesurfer_dir: Ruta a la carpeta FreeSurfer del paciente.

    Guarda los archivos combinados en la carpeta 'surf' dentro de FreeSurfer.
    """
    
    def load_surf_and_thickness(hemi, path):
        surf_path = os.path.join(path, 'surf', f'{hemi}.pial')
        thickness_path = os.path.join(path, 'surf', f'{hemi}.thickness')

        if not os.path.exists(surf_path) or not os.path.exists(thickness_path):
            raise FileNotFoundError(f"No se encontraron los archivos de {hemi} en {path}")

        surf = nib.freesurfer.io.read_geometry(surf_path)
        thickness = nib.freesurfer.io.read_morph_data(thickness_path)
        return surf[0], surf[1], thickness

    
    try:
        rh_coords, rh_faces, rh_thickness = load_surf_and_thickness('rh', freesurfer_dir)
        lh_coords, lh_faces, lh_thickness = load_surf_and_thickness('lh', freesurfer_dir)

        # Combinar coordenadas y caras de ambos hemisferios
        combined_coords = np.concatenate([rh_coords, lh_coords])
        combined_faces = np.concatenate([rh_faces, lh_faces + len(rh_coords)])

        # Combinar valores de grosor de ambos hemisferios
        combined_thickness = np.concatenate([rh_thickness, lh_thickness])

        # Guardar el archivo pial unificado
        combined_pial_path = os.path.join(freesurfer_dir, 'surf', 'combined.pial')
        nib.freesurfer.io.write_geometry(combined_pial_path, combined_coords, combined_faces)
        print(f"Archivo pial unificado guardado en: {combined_pial_path}")

        # Guardar el archivo de grosor unificado
        combined_thickness_path = os.path.join(freesurfer_dir, 'surf', 'combined.thickness')
        nib.freesurfer.io.write_morph_data(combined_thickness_path, combined_thickness)
        print(f"Archivo de grosor unificado guardado en: {combined_thickness_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}")