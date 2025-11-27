import os
import pydicom

def formatear_edad(edad):
    if edad.endswith("Y"):  # Si la edad termina con "Y" (de años)
        return str(int(edad[:-1])) + " años"
    return str(int(edad)) + " años"

def leer_edad(dicom_dir):
    # Buscar en los archivos DICOM en el directorio proporcionado
    for root, dirs, files in os.walk(dicom_dir):
        for file in files:
            if file.endswith(".dcm"):
                dicom_path = os.path.join(root, file)
                ds = pydicom.dcmread(dicom_path)
                edad = ds.get("PatientAge", None)  # Obtener la edad del paciente
                if edad:
                    return formatear_edad(edad)
    raise FileNotFoundError("No se encontró ningún archivo DICOM en el directorio proporcionado o no tiene información de edad.")

if _name_ == "_main_":
    import sys
    dicom_dir = sys.argv[1]  # Obtener la ruta del directorio DICOM desde los argumentos
    edad = leer_edad(dicom_dir)
    print(edad)