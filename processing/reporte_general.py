def generate_morphometric_report_general(dicom_dir, subjects_dir, base_control_path):
    
    
    import pydicom
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    from reportlab.lib import styles
    from reportlab.platypus import Paragraph
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    import PyPDF2
    import io
    from PIL import Image
    import pandas as pd
    import os
    import subprocess
    import re
    import numpy as np

    def formatear_nombre(nombre_dicom):
        if not nombre_dicom:
            return "Desconocido"

        # Convertir el objeto PersonName a una cadena de texto
        nombre_texto = str(nombre_dicom)

        # Dividir el nombre usando el caracter '^'
        partes = nombre_texto.split('^')

        # Invertir el orden y capitalizar cada parte
        partes_formateadas = [parte.title() for parte in partes[::-1] if parte]

        # Unir las partes con espacios
        nombre_formateado = ' '.join(partes_formateadas)
        return nombre_formateado


    def formatear_edad(edad_dicom):
        return edad_dicom[1:3]

    def formatear_fecha(fecha_dicom):
        meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
        año, mes, dia = fecha_dicom[:4], int(fecha_dicom[4:6]), fecha_dicom[6:8]
        mes_texto = meses[mes - 1]
        return f"{dia} - {mes_texto} - {año}"

    def buscar_primer_dicom(dicom_dir):
        # Buscar archivos DICOM en el directorio dado
        for root, dirs, files in os.walk(dicom_dir):
            for file in files:
                if file.endswith(".dcm"):
                    return os.path.join(root, file)
        return None

    # Cargar el archivo DICOM
   
    # Base directory is the one provided by the user (where FreeSurfer is located)
    base_dir = dicom_dir

    # Definir rutas automáticas a las carpetas de FreeSurfer
    path_stats = os.path.join(subjects_dir, 'stats')
    path_surf = os.path.join(subjects_dir, 'surf')
    path_mri = os.path.join(subjects_dir, 'mri')

    
    # Verificación para asegurarse de que las rutas existen
    if not os.path.exists(path_stats):
        raise FileNotFoundError(f"No se encontró la carpeta 'stats' en la ruta calculada: {path_stats}")

    if not os.path.exists(path_surf):
        raise FileNotFoundError(f"No se encontró la carpeta 'surf' en la ruta calculada: {path_surf}")

    if not os.path.exists(path_mri):
        raise FileNotFoundError(f"No se encontró la carpeta 'mri' en la ruta calculada: {path_mri}")
    

    dicom_path = buscar_primer_dicom(dicom_dir)
    if dicom_path:
        ds = pydicom.dcmread(dicom_path)
        # Extraer datos del paciente del archivo DICOM
        datos_paciente = {
            "Paciente": formatear_nombre(ds.get("PatientName", "Desconocido")),
            "Edad": formatear_edad(ds.get("PatientAge", "00")),
            "Sexo": ds.get("PatientSex", "Desconocido"),
            "Fecha del estudio": formatear_fecha(ds.get("StudyDate", "00000000")),
            "Accession Number": ds.get("AccessionNumber", "Desconocido"),
            "Patient ID": ds.get("PatientID", "Desconocido")
        }
    else:
        raise FileNotFoundError(f"No se encontró ningún archivo DICOM en el directorio: {dicom_dir}")



    # Registra las fuentes OpenSans Light y OpenSans Bold
    pdfmetrics.registerFont(TTFont('OpenSansLight', '//home/usuario/Bibliografia/pipeline_v2/recursos/OpenSans-Light.ttf'))
    pdfmetrics.registerFont(TTFont('OpenSansRegular', '//home/usuario/Bibliografia/pipeline_v2/recursos/OpenSans-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('ArialUnicode', '//home/usuario/Bibliografia/pipeline_v2/recursos/Arial-Unicode-Regular.ttf'))

    def formatear_porcentaje(num):
        num = float(num)
        if num == 100:
            return "100.00"
        else:
            return "{:.2f}".format(num)


    def formatear_rango(rango):
        # Dividir el rango en dos números
        inicio, fin = rango.split(' - ')

        # Formatear cada número utilizando la función 'formatear_porcentaje'
        inicio_formateado = formatear_porcentaje(float(inicio))
        fin_formateado = formatear_porcentaje(float(fin))

        # Unir de nuevo los números formateados
        return f"{inicio_formateado} - {fin_formateado}"

    # Lee el PDF existente (template) para obtener las dimensiones y número de páginas
    template_pdf_path = '/home/usuario/Bibliografia/pipeline_v2/recursos/Copy of PDF Report.pdf'
    existing_pdf = PyPDF2.PdfReader(open(template_pdf_path, "rb"))
    num_pages = len(existing_pdf.pages)
    template_page = existing_pdf.pages[0]
    template_dims = template_page.mediabox

    # Crea un objeto writer para el nuevo PDF
    output = PyPDF2.PdfWriter()

    #Cargar excel de volumetria para exportar asimetria de sustancia blanca
    archivo_xlsx = os.path.join(path_stats, 'volumetria.xlsx')
    df_asimetria_sust_blanca = pd.read_excel(archivo_xlsx, sheet_name='Asimetrias')
    # Primero, necesitamos la función 'formatear_rango' (cópiala de más abajo en tu script)
    def formatear_rango(rango):
        # Asegurarnos de que el rango sea un string antes de dividir
        if not isinstance(rango, str):
            rango = str(rango)
        inicio, fin = rango.split(' - ')
        # Formatear cada número (asumiendo que formatear_porcentaje está definida más abajo)
        inicio_formateado = formatear_porcentaje(float(inicio))
        fin_formateado = formatear_porcentaje(float(fin))
        return f"{inicio_formateado} - {fin_formateado}"

    def formatear_porcentaje(num):
        num = float(num)
        if num == 100:
            return "100.00"
        else:
            return "{:.2f}".format(num)

    # Extraer la fila
    fila_sb = df_asimetria_sust_blanca[df_asimetria_sust_blanca['Region'] == 'Sustancia Blanca Cerebral'].copy()

    # Preparar la fila para que coincida con el DataFrame de destino
    if not fila_sb.empty:
        # 1. Renombrar 'Region' a 'Measure:GrayVol'
        fila_sb = fila_sb.rename(columns={'Region': 'Measure:GrayVol'})
        
        # 2. Renombrar y formatear 'Asimetria' (de número a string formateado)
        fila_sb['Asimetria'] = fila_sb['Asimetria'].apply(lambda x: "{:.2f}".format(float(x)))
        
        # 3. Formatear el rango (usando la función que definimos arriba)
        fila_sb['Rango_normal_ajustado_por_edad_según_AIP'] = fila_sb['Rango_normal_ajustado_por_edad_según_AIP'].apply(formatear_rango)

        # 4. Añadir la columna 'Mediana' que falta (la llenamos con NaN)
        fila_sb['Mediana'] = np.nan
    
    # Cargar el archivo Excel de volumenes especificos
    archivo_xlsx = os.path.join(path_stats, 'Especificos.xlsx')
    df = pd.read_excel(archivo_xlsx, sheet_name='Volumenes')
    df_asimetrias = pd.read_excel(archivo_xlsx, sheet_name='Asimetrias')

    # Formatear los datos de asimetrías
    df_asimetrias['LI% (Volrel)'] = df_asimetrias['LI% (Volrel)'].apply(lambda x: "{:.2f}".format(float(x)))


    asimetrias_validas = {
        'Validas': [
            'Espesor cortical derecho (mm)',
            'Frontal',
            'Parietal',
            'Temporal',
            'Occipital',
            'Amígdala',
            'Ganglios basales: estriado',
            'Ganglios basales: tálamo',
            'Hipocampo',
            'Sustancia gris corteza izquierda',
            'Ventrículos Laterales',
        ],
    }

    # Organizar datos
    datos_asimetria = {}
    for categoria, regiones in asimetrias_validas.items():
        # ... (tu código de filtrado va aquí) ...
        datos_filtrados = df_asimetrias[df_asimetrias['Measure:GrayVol'].isin(regiones)].copy()
        columnas_a_seleccionar = ['Measure:GrayVol', 'LI% (Volrel)', 'Mediana', 'rango normal', 'IC_99%_Bajo', "IC_99%_Alto"]
        columnas_existentes = [col for col in columnas_a_seleccionar if col in datos_filtrados.columns]
        df_seleccionado = datos_filtrados[columnas_existentes].sort_values(by='Measure:GrayVol')

        # --- MODIFICACIÓN AQUÍ ---
        # Renombra AMBAS columnas en el DataFrame antes de guardarlo
        df_renombrado = df_seleccionado.rename(columns={
            'rango normal': 'Rango_normal_ajustado_por_edad_según_AIP',
            'LI% (Volrel)': 'Asimetria'  # <-- Añade este renombrado aquí
        })
        
        df_renombrado.loc[:, 'Rango_normal_ajustado_por_edad_según_AIP'] = df_renombrado['Rango_normal_ajustado_por_edad_según_AIP'].apply(formatear_rango)

    # Guardar el DataFrame final en el diccionario
    datos_asimetria[categoria] = df_renombrado

    if 'Validas' in datos_asimetria and not fila_sb.empty:
        # Alinear columnas por si el orden es diferente
        columnas_destino = datos_asimetria['Validas'].columns
        fila_sb_alineada = fila_sb[columnas_destino]

        datos_asimetria['Validas'] = pd.concat(
            [datos_asimetria['Validas'], fila_sb_alineada],
            ignore_index=True
        )

    #renombramos asimetrias
    mapa_nombres = {
        'Espesor cortical derecho (mm)': 'Espesor cortical ',
        'Sustancia gris corteza izquierda': 'Sustancia gris cortical '
    }
    
    # CORRECTO
    datos_asimetria['Validas']['Measure:GrayVol'] = datos_asimetria['Validas']['Measure:GrayVol'].replace(mapa_nombres)

     #------------Funciones----------------------------------------------
    # Formatear la columna 'Rango normal ajustado por edad según Z scores'
    def formatear_rango_con_dos_decimales(rango):
        inicio, fin = rango.split(' - ')
        inicio_formateado = f"{float(inicio):.2f}"
        fin_formateado = f"{float(fin):.2f}"
        return f"{inicio_formateado} - {fin_formateado}"

    
    #conversion de Volumen en mm3 a volumen en cm3
    #aseguro que los valores sean numericos
    df['Volumen mm3 (sujeto)'] = pd.to_numeric(df['Volumen mm3 (sujeto)'], errors='coerce')

    # Lista de las filas que son espesores y no deben convertirse
    filas_espesor = [
        'Espesor cortical derecho (mm)',
        'Espesor cortical izquierdo (mm)',
        'Espesor cortical promedio (mm)'
    ]

    #   Identifico las filas que NO son de espesor para convertirlas.
    #    Asumo que los nombres de las estructuras están en el índice del DataFrame.
    #    El símbolo '~' invierte la selección, por lo que seleccionamos todo lo que NO está en la lista.
    filas_a_convertir = ~df['Measure:GrayVol'].isin(filas_espesor)

    # 3. Aplico la conversión a cm³ SOLO a las filas seleccionadas (las que no son espesores)
    df.loc[filas_a_convertir, 'Volumen mm3 (sujeto)'] = df.loc[filas_a_convertir, 'Volumen mm3 (sujeto)'] / 1000

    #renombrar columna
    df = df.rename(columns={'Volumen mm3 (sujeto)': 'Volumen_cm3'})

    # Conversión de 'Volumen_cm3' para asegurar dos decimales
    df['Volumen_cm3'] = df['Volumen_cm3'].apply(lambda x: "{:.2f}".format(float(x)))

    # Aplicar la función modificada a la columna 'Volumen_%VIT'
    df['Volumen_%VIT'] = df['Volrel% (sujeto)'].apply(formatear_porcentaje)

    # Aplicar la función a la columna 'Volumen_%VIT'

    # Agrupar los datos de IC_99%_Bajo y IC_99%_Alto en una sola columna
    df['Rango_normal_ajustado_por_edad_según_%VIT'] = df.apply(
        lambda row: f"{row['IC_99%_Bajo']} - {row['IC_99%_Alto']}", axis=1
    )

    # Reorganizar las columnas
    df = df[['Measure:GrayVol', 'Volumen_cm3', 'Volrel% (sujeto)',
            'Rango_normal_ajustado_por_edad_según_%VIT', 'Percentil (sujeto)',
            'Dentro_de_Umbral_±3.5', 'Mediana', 'IC_95%_Bajo', 'IC_95%_Alto',
            'IC_99%_Bajo', 'IC_99%_Alto']]

    # Asegurar el formato de dos decimales para todas las columnas numéricas
    df[['Percentil (sujeto)']] = df[['Percentil (sujeto)']].applymap(
        lambda x: f"{x:.2f}" if not pd.isna(x) else "0.00"
    )

    df['Rango_normal_ajustado_por_edad_según_%VIT'] = df['Rango_normal_ajustado_por_edad_según_%VIT'].apply(formatear_rango)
    # Aplicar la función de formateo a la columna 'Rango_normal_ajustado_por_edad_según_AIP'
    #df_asimetrias['Rango_normal_ajustado_por_edad_según_AIP'] = df_asimetrias['Rango_normal_ajustado_por_edad_según_AIP'].apply(formatear_rango_con_dos_decimales)

    # Categorías
    # Categorías

    categorias = {
    'Valores Globales': [
        'Volumen cerebral total',
        'Sustancia gris total',
        'Sustancia blanca total',
        'Espesor cortical promedio (mm)',
    ],
    'Volumen de Estructuras Subcorticales': [
        'Amígdala',
        'Hipocampo',
        'Ganglios basales: tálamo',
        'Ganglios basales: estriado',
        'Ventrículos Laterales',
        'Cuerpo Calloso'
    ],

    'Volumen de sustancia gris de lobulos corticales': [
            'Frontal',
            'Parietal',
            'Temporal',
            'Occipital'
    ],

    'Espesores corticales por hemisferio':[
        'Espesor cortical derecho (mm)',
        'Espesor cortical izquierdo (mm)'
    ],
    
    }


    # Organizar datos

    # 1. Define los nombres que quieres cambiar
    mapa_nombres = {
        'Espesor cortical derecho (mm)': 'Espesor cortical derecho ',
        'Espesor cortical izquierdo (mm)': 'Espesor cortical izquierdo '
    }

    datos_organizados = {}  # diccionario a completarse...
    for categoria, regiones in categorias.items():
        # 1. Filtrar (usa los nombres originales con (mm))
        #    Añadimos .copy() para evitar un 'SettingWithCopyWarning'
        datos_filtrados = df[df['Measure:GrayVol'].isin(regiones)].copy()

        # --- INICIO DE LA MODIFICACIÓN ---

        # 2. Reemplazar los nombres en la columna 'Measure:GrayVol'
        #    Esto solo afecta a las filas que coincidan con el mapa_nombres
        datos_filtrados['Measure:GrayVol'] = datos_filtrados['Measure:GrayVol'].replace(mapa_nombres)

        # --- FIN DE LA MODIFICACIÓN ---

        # 3. Guardar el DataFrame modificado
        datos_organizados[categoria] = datos_filtrados.sort_values(by='Measure:GrayVol')[
            ['Measure:GrayVol', 'Volumen_cm3', 'Volrel% (sujeto)', 'Rango_normal_ajustado_por_edad_según_%VIT', "Percentil (sujeto)"]
        ]
    df_globales = datos_organizados['Valores Globales']

    df_globales = df_globales.rename(columns={
        'Rango_normal_ajustado_por_edad_según_%VIT': 'Rango Normal',
        'Volumen_cm3': 'Valores',
        'Volrel% (sujeto)': 'Vol%. rel. VTI',
        'Percentil (sujeto)': 'Percentil'
    })
    df_globales = df_globales.set_index('Measure:GrayVol')
    df_globales = df_globales.T

    #-------------------------------------------------------------------------

    # Agregar varias imágenes y modificar su tamaño
    def dibujar_imagen_escalada(canvas, ruta_imagen, x, y, factor_escala):
        """Carga, escala y dibuja una imagen en el canvas."""
        imagen = Image.open(ruta_imagen)  #
        ancho_original, alto_original = imagen.size

        ancho_escalado = ancho_original * factor_escala
        alto_escalado = alto_original * factor_escala

        canvas.drawImage(ruta_imagen, x, y, width=ancho_escalado, height=alto_escalado)

    #----------------------------------------------------------------------------------
    # Función para añadir contenido a una página específica
    def create_page_content(page_number):
        packet = io.BytesIO()  # io.BytesIO() crea un archivo virtual en memoria. Esto eprmite generar un pdf temporal en memoria sin escribirlo en disco.
        can = canvas.Canvas(packet, pagesize=(template_dims[2], template_dims[3]))  # canvas.Canvas(...) crea un lienzo en blanco sobre el cual dibujar texto, imágenes y formas.
        #packet indica que el pdf se genera en el buffer de memori. pagesize define el tamaño de la pagina utilizando el pdf template, edonde template_dims[2] es el ancho y template_dims[3] es el alto.

        # Posiciones iniciales para la escritura de los datos
        x_position = 20
        x_position_region = 20
        x_position_volumen_cm3 = 180  # Ajusta estas posiciones según sea necesario
        x_position_volumen_vit = 343
        x_position_rango_normal = 450
        x_position_percentil = 540


        # Función para centrar el texto en una columna
        def centrar_texto(canvas, texto, x_posicion_inicial, ancho_columna, y, fuente, tamano_fuente):
                """
                Parámetros:

                canvas → objeto Canvas de ReportLab donde se va a dibujar el texto.

                texto → el string que se quiere escribir.

                x_posicion_inicial → coordenada X del borde izquierdo de la columna.

                ancho_columna → ancho total de la columna (en puntos).

                y → coordenada vertical donde se dibujará el texto.

                fuente → nombre de la fuente usada ("OpenSansLight", "Helvetica", etc.).

                tamano_fuente → tamaño del texto en puntos.
                """
                ancho_texto = pdfmetrics.stringWidth(texto, fuente, tamano_fuente)  # pdfmetrics.stringWidth() → función de ReportLab que devuelve el ancho del texto en puntos según la fuente y tamaño especificados.
                x_centro = x_posicion_inicial + (ancho_columna - ancho_texto) / 2  # calcula el centro de la columna
                canvas.drawString(x_centro, y, texto)  # escribe el texto en el centro de la columna

        #----------------------------------------------------------------------------------
        # Página 1

        if page_number == 0:
            # Configura la fuente y el color para el título
            can.setFont("OpenSansLight", 20)
            can.setFillColorRGB(0.45, 0.45, 0.45)  # Color gris
            can.drawString(170, 815, "Reporte de Morfometría Cerebral-General")  # Ajusta estas coordenadas según sea necesario

            # POSICIONES INICIALES PARA LA PRIMERA FILA
            y_position_campos = 780  # Posición en Y para los nombres de los campos de la primera fila
            y_position_datos = 765   # Posición en Y para los datos de la primera fila
            x_position = 172         # Posición inicial en X
            incremento_x = 175       # Incremento en X para el siguiente campo

            # POSICIONES PARA LA SEGUNDA FILA
            y_position_campos_fila2 = 745  # Posición en Y para los nombres de los campos de la segunda fila
            y_position_datos_fila2 = 730  # Posición en Y para los datos de la segunda fila

            # Escribe los nombres de los campos y los datos
            contador_campos = 0  # Contador para saber cuándo cambiar de fila
            for campo, dato in datos_paciente.items():
                # Establece el color para el nombre del campo
                can.setFillColorRGB(0.45, 0.45, 0.45)  # Color gris #737373

                # Escribe el nombre del campo en negrita
                can.setFont("OpenSansRegular", 9)
                can.drawString(x_position, y_position_campos, campo)

                # Cambia el color de vuelta al negro para los datos
                can.setFillColorRGB(0, 0, 0)  # Color negro

                # Escribe el dato en fuente normal
                can.setFont("OpenSansLight", 9)
                can.drawString(x_position, y_position_datos, dato)

                contador_campos += 1
                if contador_campos == 3:  # Después de dibujar tres campos, cambia a la segunda fila
                    x_position = 172  # Reinicia la posición en X para la segunda fila
                    y_position_campos = y_position_campos_fila2
                    y_position_datos = y_position_datos_fila2
                else:
                    # Mueve a la siguiente columna
                    x_position += incremento_x

            # Fin del encabezado
            #----------------------------------------------------------------------------
            # Configura la fuente y el color para texto adicional
            can.setFont("OpenSansLight", 11)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Ejemplo de color azul
            can.drawString(193, 698, "Volúmenes [cm³] y espesores [mm] globales")
            can.drawString(193, 610, "Control de calidad de la segmentación")
            
            #Titulos de imagenes
            can.setFont("OpenSansLight",8.5)
            can.setFillColorRGB(0.45, 0.45, 0.45)  # Ejemplo de color azul
            can.drawString(335, 370, "Volúmenes de sustancia gris")
            can.drawString(457, 370, "Volúmenes-espesores generales")
            can.drawString(329, 255, "Espesores de Lóbulos coticales")
            can.drawString(485, 255, "Ventrículos laterales")
            can.drawString(355, 140, "Sustancia blanca")
            can.drawString(495, 140, "Sustancia gris")


            # Rutas de las imágenes
            ruta_imagen_1 = os.path.join(path_mri, 'mask', 'macroestructuras_especificos.png')
            ruta_imagen_2 = os.path.join(path_stats, 'graficos_temporales', 'Sustancia_blanca_total_vs_tiempo.png')
            ruta_imagen_3 = os.path.join(path_stats, 'graficos_temporales', 'Sustancia_gris_total_vs_tiempo.png')
            ruta_imagen_4 = os.path.join(path_stats, 'graficos_temporales', 'Ventrículos_Laterales_vs_tiempo.png')
            ruta_imagen_5 = os.path.join(path_stats, 'pentagono_sustgris.png')
            ruta_imagen_6 = os.path.join(path_stats, 'pentagono_volumenes_general.png')
            ruta_imagen_7 = os.path.join(path_stats, 'pentagono_espesores_lobulos.png')

            # Dibuja las imágenes con factores de escala diferentes (el primer parámetro ajusta posición en X y el 2do en Y)
            dibujar_imagen_escalada(can, ruta_imagen_1, 70, 430, factor_escala=0.23)
            dibujar_imagen_escalada(can, ruta_imagen_2, 327, 50, factor_escala=0.055)
            dibujar_imagen_escalada(can, ruta_imagen_3, 457, 50, factor_escala=0.055)
            dibujar_imagen_escalada(can, ruta_imagen_4, 457, 160, factor_escala=0.055)
            dibujar_imagen_escalada(can, ruta_imagen_5, 327, 280, factor_escala=0.0556)
            dibujar_imagen_escalada(can, ruta_imagen_6, 457, 280, factor_escala=0.051)
            dibujar_imagen_escalada(can, ruta_imagen_7, 327, 160, factor_escala=0.05428)

            
        # Asumiendo que tienes las columnas con anchos definidos. Se definen anchos fijos para cada columna.
            ancho_columna_volumen_cerebral_total = 60
            ancho_columna_volumen_Sustancia_gris_total = 60
            ancho_columna_Espesor_cortical_derecho = 60
            ancho_columna_Espesor_cortical_izquierdo = 60
            ancho_columna_volumen_cm3 = 60
            ancho_columna_volumen_vit = 60
            ancho_columna_rango_normal = 60
            ancho_columna_rango_percentil = 60

            if page_number == 0:
                y_position = 663
                x_position_volumen_cerebral_total = 145
                x_position_volumen_Sustancia_gris_total = 245  # Ajusta estas posiciones según sea necesario
                x_position_Espesor_cortical_derecho = 345
                x_position_Espesor_cortical_izquierdo = 445

                # Dibuja los encabezados de las columnas
                can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
                can.setFont("OpenSansRegular", 10)
                can.drawString(x_position_volumen_cerebral_total - 15, y_position + 15, "Volumen cerebral total")
                can.setFont("OpenSansRegular", 10)  # Vuelve al tamaño de fuente normal
                can.drawString(x_position_volumen_Sustancia_gris_total + 15, y_position + 15, "Sustancia gris")
                can.drawString(x_position_Espesor_cortical_derecho+20, y_position + 15, "Sustancia blanca")
                can.drawString(x_position_Espesor_cortical_izquierdo + 17, y_position + 15, "Espesor cortical medio")
                can.setFont("OpenSansLight", 10)


            # 1. Obtenemos la fila 'Rango Normal' ANTES del bucle
            try:
                rango_data = df_globales.loc['Rango Normal']
            except KeyError:
                print("Advertencia: No se encontró la fila 'Rango Normal' en el DataFrame.")
                rango_data = None

            # 2. Iteramos sobre el DataFrame
            for nombre_metrica, fila in df_globales.iterrows():
            
                # CASO A: Es la fila 'Rango Normal'
                if nombre_metrica == 'Rango Normal':
                    # La saltamos, porque sus datos ya están fusionados
                    continue

                # CASO B: Es la fila de Volumen en cm3
                elif nombre_metrica == 'Volumen [cm3]' and rango_data is not None:
                    # Dibujar las 3 primeras columnas normalmente
                    centrar_texto(can, str(fila['Volumen cerebral total']), x_position_volumen_cerebral_total+5, ancho_columna_volumen_cerebral_total, y_position-5, "OpenSansLight", 9)
                    centrar_texto(can, str(fila['Sustancia gris total']), x_position_volumen_Sustancia_gris_total+17, ancho_columna_volumen_Sustancia_gris_total, y_position-5, "OpenSansLight", 9)
                    centrar_texto(can, str(fila['Sustancia blanca total']), x_position_Espesor_cortical_derecho+30, ancho_columna_Espesor_cortical_derecho, y_position-5, "OpenSansLight", 9)
                    
                    # Para la 4ta columna (Espesor), combinar el valor con su rango
                    texto_espesor = f"{fila['Espesor cortical promedio (mm)']} ({rango_data['Espesor cortical promedio (mm)']})"
                    centrar_texto(can, texto_espesor, x_position_Espesor_cortical_izquierdo+33, ancho_columna_Espesor_cortical_izquierdo, y_position-5, "OpenSansLight", 9)

                    can.drawString(x_position_region+20, y_position, nombre_metrica)
                    y_position -= 13

                # CASO C: Es la fila de Volumen relativo
                elif nombre_metrica == 'Vol%. rel. VTI' and rango_data is not None:
                    # Para las 3 primeras columnas, combinar el valor con su rango
                    texto_col1 = f"{fila['Volumen cerebral total']} ({rango_data['Volumen cerebral total']})"
                    centrar_texto(can, texto_col1, x_position_volumen_cerebral_total+5, ancho_columna_volumen_cerebral_total, y_position-5, "OpenSansLight", 9)
                    
                    texto_col2 = f"{fila['Sustancia gris total']} ({rango_data['Sustancia gris total']})"
                    centrar_texto(can, texto_col2, x_position_volumen_Sustancia_gris_total+15, ancho_columna_volumen_Sustancia_gris_total, y_position-5, "OpenSansLight", 9)

                    texto_col3 = f"{fila['Sustancia blanca total']} ({rango_data['Sustancia blanca total']})"
                    centrar_texto(can, texto_col3, x_position_Espesor_cortical_derecho+30, ancho_columna_Espesor_cortical_derecho, y_position-5, "OpenSansLight", 9)
                    
                    # Para la 4ta columna (Espesor), dibujar un guion
                    centrar_texto(can, '-', x_position_Espesor_cortical_izquierdo+33, ancho_columna_Espesor_cortical_izquierdo, y_position-5, "OpenSansLight", 9)

                    # Escribir el nombre de la métrica sin "(Rango Normal)"
                    can.drawString(x_position_region+20, y_position, 'Vol%. rel. VTI')
                    y_position -= 13

                # CASO D: Cualquier otra fila (ej. Percentil)
                else:
                    # Dibujar la fila normalmente
                    centrar_texto(can, str(fila['Volumen cerebral total']), x_position_volumen_cerebral_total+5, ancho_columna_volumen_cerebral_total, y_position-5, "OpenSansLight", 9)
                    centrar_texto(can, str(fila['Sustancia gris total']), x_position_volumen_Sustancia_gris_total+15, ancho_columna_volumen_Sustancia_gris_total, y_position-5, "OpenSansLight", 9)
                    centrar_texto(can, str(fila['Sustancia blanca total']), x_position_Espesor_cortical_derecho+30, ancho_columna_Espesor_cortical_derecho, y_position-5, "OpenSansLight", 9)
                    centrar_texto(can, str(fila['Espesor cortical promedio (mm)']), x_position_Espesor_cortical_izquierdo+33, ancho_columna_Espesor_cortical_izquierdo, y_position-5, "OpenSansLight", 9)

                    can.drawString(x_position_region+20, y_position, nombre_metrica)
                    y_position -= 13
            y_position = 380

            # Dibuja los encabezados de las columnas
            can.setFillColorRGB(0.090, 0.329, 0.721)
            can.setFont("OpenSansRegular", 10)
            can.drawString(x_position_region+125, y_position, "cm³")
            can.drawString(x_position_region+165, y_position, "%VIT")
            can.drawString(x_position_region+210, y_position + 10, "Rango")
            can.drawString(x_position_region+210, y_position, "Normal")
            can.drawString(x_position_region+258, y_position, "Percentil")

            # Dibuja los encabezados de las columnas para espesores, cambia cm3 por mm
            can.drawString(x_position_region+125, y_position-268, "mm")
            can.drawString(x_position_region+165, y_position-268, "%VIT")
            can.drawString(x_position_region+210, y_position-260, "Rango")
            can.drawString(x_position_region+210, y_position-268, "Normal")
            can.drawString(x_position_region+258, y_position-268, "Percentil")        


            for categoria, datos in datos_organizados.items():
                if categoria != 'Valores Globales':
                    can.setFont("OpenSansRegular", 9)
                    can.setFillColorRGB(0, 0, 0) # Color

                    if categoria == 'Volumen de Estructuras Subcorticales':
                        # Dibuja la primera línea del título
                        can.drawString(x_position_region, y_position, "Volumenes de Estructuras")
                        
                        # Define un interlineado (ej. 12 pt) y baja la posición Y
                        interlineado = 12 
                        y_position -= interlineado
                        
                        # Dibuja la segunda línea del título
                        can.drawString(x_position_region, y_position, "Subcorticales")
                    elif categoria=="Espesores corticales por hemisferio":
                        can.drawString(x_position_region, y_position, "Espesores corticales")
                        # Define un interlineado (ej. 12 pt) y baja la posición Y
                        interlineado = 12 
                        y_position -= interlineado
                        
                        # Dibuja la segunda línea del título
                        can.drawString(x_position_region, y_position, "por hemisfeio")

                    elif categoria=="Volumen de sustancia gris de lobulos corticales":
                        can.drawString(x_position_region, y_position, "Volumen de sustancia gris")
                        
                        # Define un interlineado (ej. 12 pt) y baja la posición Y
                        interlineado = 12 
                        y_position -= interlineado
                        
                        # Dibuja la segunda línea del título
                        can.drawString(x_position_region, y_position, "de lobulos corticales")  
                    
                    else:
                        # Comportamiento normal para todas las otras categorías
                        can.drawString(x_position_region, y_position, categoria)
                    
                    # Vuelve a OpenSansLight para los datos

                    can.setFont("OpenSansLight", 8)
                    can.setFillColorRGB(0.2, 0.2, 0.2) # Color
                    y_position -= 20
                    
                    for _, fila in datos.iterrows():
                        # Centrar el texto de las otras columnas (sin cambios)
                        centrar_texto(can, str(fila['Volumen_cm3']), (x_position_volumen_cm3/2)+35, ancho_columna_volumen_cm3, y_position, "OpenSansLight", 10)
                        centrar_texto(can, str(fila['Rango_normal_ajustado_por_edad_según_%VIT']), x_position_rango_normal/2, ancho_columna_rango_normal, y_position, "OpenSansLight", 10)
                        centrar_texto(can, str(fila['Percentil (sujeto)']), x_position_percentil/2, ancho_columna_rango_normal, y_position, "OpenSansLight", 10)

                        
                        # Comprobar si la categoría es la de espesores
                        if categoria == 'Espesores corticales por hemisferio':
                            texto_volrel = '-'
                        else:
                            texto_volrel = str(fila['Volrel% (sujeto)'])
                        
                        # Dibujar el texto correspondiente para la columna Volrel
                        centrar_texto(can, texto_volrel, x_position_volumen_vit/2, ancho_columna_volumen_vit, y_position, "OpenSansLight", 10)


                        # Dibujar el nombre de la región (sin cambios)
                        can.drawString(x_position_region , y_position, fila['Measure:GrayVol'])

                        y_position -= 20    
                        if y_position < 15:
                            # Maneja el cambio de página
                            can.showPage()
                            can.setFont("OpenSansLight", 9)
                            can.setFillColorRGB(0, 0, 0)
                            y_position = 750



        elif page_number == 1:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            #-----Columnas para Asimetrias--------
            # (Nota: Aquí tienes "Mediana" dos veces, quizás querías "Rango normal" en la tercera)
            can.drawString(x_position_volumen_cm3+135, y_position - 142, "Asimetria %")
            #can.drawString(x_position_volumen_vit, y_position - 160, "Mediana")
            can.drawString(x_position_rango_normal+20, y_position - 142, "Rango normal") # <-- Corregido (basado en tu bucle)


            can.setFont("OpenSansLight", 9)

             # Agregar datos de Asimetrias antes del aviso de aclaración
            y_position_asimetrias_left = y_position - 50  # Ajusta la posición según sea necesario
            # ... (variables 'y_position_asimetrias_right' y 'x_position_right_column' no se usan, puedes borrarlas si quieres)

            can.setFont("OpenSansRegular", 12)
            can.drawString(x_position_region+5, y_position_asimetrias_left + 25, "Asimetría Interhemisférica Porcentual")
            can.setFont("OpenSansLight", 9)

            # Texto sobre asimetrias
            # Define el estilo del párrafo
            estilo = styles.getSampleStyleSheet()["Normal"]
            estilo.fontName = "OpenSansLight"
            estilo.fontSize = 9
            estilo.leading = 14  # Ajusta el interlineado si es necesario
            estilo.textColor = (0.35, 0.35, 0.35)  # Color gris
            estilo.alignment = styles.TA_JUSTIFY  # Alineación justificada
            texto_asimetrias = """Esta métrica se calculó determinando la diferencia de volúmenes entre estructuras homólogas de ambos hemisferios, dividida por el promedio de los volúmenes de estas estructuras, proporcionando una medida normalizada de la disparidad volumétrica relativa.
            Los calculos se realizarón tomando el hemisferio izquierdo como referencia, es así que, la presencia de un valor negativo indica un volumen mayor en el hemisferio derecho."""
            # Crea un objeto Paragraph con el texto y el estilo
            parrafo_asimetrias = Paragraph(texto_asimetrias, estilo)

            # Dibuja el párrafo en el canvas
            # Ajusta x, y y ancho_max según sea necesario
            ancho_max = 530
            alto_max = 100
            parrafo_asimetrias.wrapOn(can, ancho_max, alto_max)
            parrafo_asimetrias.drawOn(can, 25, 780- alto_max)  # Ajusta x, y según sea necesario

            # --- Bucle para dibujar los datos de asimetría ---
            # (Ajusta la 'y_position' inicial para que empiece debajo del párrafo)
            y_position = 750 - alto_max - 50 # <-- Posición inicial ajustada

            for categoria, datos in datos_asimetria.items():
                if categoria == 'Validas':
                    # Vuelve a OpenSansLight para los datos
                    can.setFont("OpenSansLight", 9)
                    can.setFillColorRGB(0.2, 0.2, 0.2)  # Color 
                    # y_position -= 20 # (Quita este para no crear un espacio extra antes de la primera fila)

                    for _, fila in datos.iterrows():
                        # Centrar el texto de las columnas y dibujar
                        centrar_texto(can, str(fila['Asimetria']), x_position_volumen_cm3+105, 100, y_position, "OpenSansLight", 10)
                        #centrar_texto(can, str(fila['Mediana']), x_position_volumen_vit, 100, y_position, "OpenSansLight", 10)
                        centrar_texto(can, str(fila['Rango_normal_ajustado_por_edad_según_AIP']), x_position_rango_normal-5, 100, y_position, "OpenSansLight", 10)

                        can.drawString(x_position_region +5, y_position, fila['Measure:GrayVol'])

                        y_position -= 20    
                        if y_position < 15:
                            # Maneja el cambio de página
                            can.showPage()
                            can.setFont("OpenSansLight", 9)
                            can.setFillColorRGB(0, 0, 0)
                            y_position = 750

                    y_position -= 20

            #Imagen 3D lobulos corticales
            can.setFont("OpenSansLight", 11)
            can.setFillColorRGB(0.45, 0.45, 0.45)  
            can.drawString(205, 310, "Recontruscción de Lóbulos corticales")
            # Rutas de las imágenes
            ruta_imagen_1 = os.path.join(path_mri, 'mask', 'lobulos_vistas_combinadas.png')
            dibujar_imagen_escalada(can, ruta_imagen_1, 44, 127, factor_escala=0.21)
        #-----------------------------------------------------------------------------------
        can.save()
        packet.seek(0)
        return PyPDF2.PdfReader(packet)

    #---------------------------------------------------------------------------
    # Añadir contenido a cada página y combinarlo con el template
    for i in range(num_pages):
        # Crea contenido para la página actual
        new_pdf_reader = create_page_content(i)
        new_pdf_page = new_pdf_reader.pages[0]

        # Obtiene la página correspondiente del PDF de plantilla
        template_pdf_page = existing_pdf.pages[i]

        # Fusiona la página de plantilla con el nuevo contenido
        template_pdf_page.merge_page(new_pdf_page)

        # Añade la página combinada al documento final
        output.add_page(template_pdf_page)

    def comprimir_pdf(input_path, output_path):
        gs_command = [
            "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/printer", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={output_path}", input_path
        ]
        subprocess.run(gs_command, check=True)

    # Generar y guardar el PDF original
    final_pdf_path_original = os.path.join(path_stats, 'Reporte_morf_esp.pdf')
    with open(final_pdf_path_original, "wb") as outputStream:
        output.write(outputStream)

    # Imprimir la ruta del archivo original
    print(f"\nArchivo PDF original generado exitosamente en: {final_pdf_path_original}")

    # Crear la versión comprimida con un nombre diferente
    final_pdf_path_comprimido = os.path.join(path_stats, 'Reporte_morf_esp_comprimido.pdf')
    comprimir_pdf(final_pdf_path_original, final_pdf_path_comprimido)

    # Imprimir la ruta del archivo comprimido
    print(f"\nArchivo PDF comprimido generado exitosamente en: {final_pdf_path_comprimido}")

