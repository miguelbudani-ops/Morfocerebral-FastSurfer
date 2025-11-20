#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import pydicom

def formatear_edad(edad):
    if edad.endswith("Y"):
        return str(int(edad[:-1])) + " años"
    return str(int(edad)) + " años"

def leer_dicom_y_extraer_info(dicom_dir):
    for root, dirs, files in os.walk(dicom_dir):
        for file in files:
            if file.endswith(".dcm"):
                dicom_path = os.path.join(root, file)
                ds = pydicom.dcmread(dicom_path)
                edad = formatear_edad(ds.get("PatientAge", "00"))
                genero = ds.get("PatientSex", "Desconocido")
                return {"edad": edad, "género": genero}
    raise FileNotFoundError("No se encontró ningún archivo DICOM en el directorio proporcionado.")

