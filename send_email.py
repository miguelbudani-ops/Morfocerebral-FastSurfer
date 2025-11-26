

# send_email.py

import sys
import smtplib
from email.message import EmailMessage
from pathlib import Path

if len(sys.argv) < 5:
    raise SystemExit(
        "Uso: send_email.py <nombre_paciente> <mensaje_path> <destinatarios_path> <reporte1.pdf> [reporte2.pdf ...]"
    )

nombre_paciente = sys.argv[1]
mensaje_path = Path(sys.argv[2])
destinatarios_path = Path(sys.argv[3])
reporte_paths = [Path(p) for p in sys.argv[4:]]

if not mensaje_path.is_file():
    raise FileNotFoundError(f"No se encontró el mensaje: {mensaje_path}")

if not destinatarios_path.is_file():
    raise FileNotFoundError(f"No se encontró la lista de destinatarios: {destinatarios_path}")

if not reporte_paths:
    raise SystemExit("Debe proporcionar al menos un PDF a adjuntar.")

pdf_paths = []
for path in reporte_paths:
    if not path.is_file():
        print(f"Advertencia: se omite {path} porque no existe.")
        continue
    pdf_paths.append(path)

if not pdf_paths:
    raise SystemExit("Ningún PDF válido para adjuntar.")

# Leer mensaje
with open(mensaje_path, "r") as f:
    mensaje = f.read()
mensaje = mensaje.replace("{nombre_paciente}", nombre_paciente)


# Leer destinatarios
with open(destinatarios_path, "r") as f:
    destinatarios = [line.strip() for line in f if line.strip()]

if not destinatarios:
    raise SystemExit("No se encontraron destinatarios válidos.")

msg = EmailMessage()
msg["Subject"] = f"Reporte Morfovolumétrico - {nombre_paciente}"
msg["From"] = "neurointecnus@gmail.com"
msg["To"] = ", ".join(destinatarios)
print("Mensaje a enviar:\n", mensaje)
msg.set_content(mensaje)

for pdf_path in pdf_paths:
    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=pdf_path.name,
        )

smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_user = "neurointecnus@gmail.com"
smtp_pass = "durk kygd wfwm jgtk"

with smtplib.SMTP(smtp_server, smtp_port) as server:
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.send_message(msg)

print(f"Correo enviado correctamente con {len(pdf_paths)} adjuntos.")
