# extract_patient_name.py
import sys
import os
import pydicom

def extract_name(dicom_dir):
    for root, _, files in os.walk(dicom_dir):
        for file in files:
            if file.lower().endswith(".dcm"):
                try:
                    path = os.path.join(root, file)
                    ds = pydicom.dcmread(path, stop_before_pixels=True)
                    name = ds.get("PatientName", None)
                    if name:
                        if isinstance(name, pydicom.valuerep.PersonName):
                            name = str(name).replace("^", "_")
                        return str(name).replace(" ", "_")
                except Exception:
                    continue
    return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    name = extract_name(sys.argv[1])
    if name:
        print(name.strip().replace(" ", "_"))