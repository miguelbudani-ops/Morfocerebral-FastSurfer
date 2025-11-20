def generate_morphometric_report(dicom_dir, subjects_dir, base_control_path):
    
    
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

    # Lee el PDF existente (template) para obtener las dimensiones y número de páginas
    template_pdf_path = '/home/usuario/Bibliografia/pipeline_v2/recursos/reporte_completo.pdf'
    existing_pdf = PyPDF2.PdfReader(open(template_pdf_path, "rb"))
    num_pages = len(existing_pdf.pages)
    template_page = existing_pdf.pages[0]
    template_dims = template_page.mediabox

    # Crea un objeto writer para el nuevo PDF
    output = PyPDF2.PdfWriter()

    #-------------------------------------------------------------------------
    #-------------------------------------------------------------------------

    # Cargar el archivo Excel de volumetría
    archivo_xlsx = os.path.join(path_stats, 'volumetria.xlsx')
    df = pd.read_excel(archivo_xlsx, sheet_name='Volumenes')
    df_asimetrias = pd.read_excel(archivo_xlsx, sheet_name='Asimetrias')

    # Formatear los datos de asimetrías
    df_asimetrias['Asimetria'] = df_asimetrias['Asimetria'].apply(lambda x: "{:.2f}".format(float(x)))



    #-------------------------------------------------------------------
    #------------Funciones----------------------------------------------
    # Formatear la columna 'Rango normal ajustado por edad según Z scores'
    def formatear_rango_con_dos_decimales(rango):
        inicio, fin = rango.split(' - ')
        inicio_formateado = f"{float(inicio):.2f}"
        fin_formateado = f"{float(fin):.2f}"
        return f"{inicio_formateado} - {fin_formateado}"

    def formatear_porcentaje(num):
        num = float(num)
        if num == 100:
            return "100.00"
        else:
            return "{:.2f}".format(num)

    # Conversión de 'Volumen_cm3' para asegurar dos decimales
    df['Volumen_cm3'] = df['Volumen_cm3'].apply(lambda x: "{:.2f}".format(float(x)))

    # Aplicar la función modificada a la columna 'Volumen_%VIT'
    df['Volumen_%VIT'] = df['Volumen_%VIT'].apply(formatear_porcentaje)

    def formatear_rango(rango):
        # Dividir el rango en dos números
        inicio, fin = rango.split(' - ')

        # Formatear cada número utilizando la función 'formatear_porcentaje'
        inicio_formateado = formatear_porcentaje(float(inicio))
        fin_formateado = formatear_porcentaje(float(fin))

        # Unir de nuevo los números formateados
        return f"{inicio_formateado} - {fin_formateado}"
    # Aplicar la función a la columna 'Volumen_%VIT'
    df['Rango_normal_ajustado_por_edad_según_%VIT'] = df['Rango_normal_ajustado_por_edad_según_%VIT'].apply(formatear_rango)
    # Aplicar la función de formateo a la columna 'Rango_normal_ajustado_por_edad_según_AIP'
    df_asimetrias['Rango_normal_ajustado_por_edad_según_AIP'] = df_asimetrias['Rango_normal_ajustado_por_edad_según_AIP'].apply(formatear_rango_con_dos_decimales)


    # Categorías
    categorias = {
        'Volúmenes Globales': [
            'Sustancia blanca cerebral derecha',
            'Sustancia blanca cerebral izquierda',
            'Sustancia blanca total',
            'Sustancia gris total',
            'Volumen Intracraneal Total estimado'
        ],
        'Volumen de Estructuras Subcorticales': [
            'Amígdala derecha',
            'Amígdala izquierda',
            'Hipocampo derecho',
            'Hipocampo izquierdo',
            'Núcleo caudado derecho',
            'Núcleo caudado izquierdo',
            'Putamen derecho',
            'Putamen izquierdo',
            'Pálido derecho',
            'Pálido izquierdo',
            'Sustancia gris subcortical',
            'Tálamo derecho',
            'Tálamo izquierdo'
        ],
        'Volúmenes del Sistema Ventricular': [
            '3er ventrículo',
            '4to ventrículo',
            'Ventrículo inf. lat. derecho',
            'Ventrículo inf. lat. izquierdo', 
            'Ventrículo lateral derecho',
            'Ventrículo lateral izquierdo'
        ],
        'Volumen de Estructuras Supratentoriales': [
            'Volumen supratentorial',
            'Volumen supratentorial sin ventrículos'
        ],
        'Volumen de Estructuras Infratentoriales': [
            'Corteza del cerebelo derecho',
            'Corteza del cerebelo izquierdo',
            'Sustancia blanca del cerebelo derecho',
            'Sustancia blanca del cerebelo izquierdo',
            'Tronco encefálico'
        ],
        'Volumen de Áreas Corticales': [
            'Volumen de la corteza derecha',
            'Volumen de la corteza izquierda',
            'Volumen total de la corteza'
        ]
    }

    # Organizar datos
    datos_organizados = {}
    for categoria, regiones in categorias.items():
        datos_filtrados = df[df['Regiones_ESP'].isin(regiones)]
        datos_organizados[categoria] = datos_filtrados.sort_values(by='Regiones_ESP')[['Regiones_ESP', 'Volumen_cm3', 'Volumen_%VIT', 'Rango_normal_ajustado_por_edad_según_%VIT']]

 
    #-------------------------------------------------------------------------

    # Agregar varias imágenes y modificar su tamaño
    def dibujar_imagen_escalada(canvas, ruta_imagen, x, y, factor_escala):
        """Carga, escala y dibuja una imagen en el canvas."""
        imagen = Image.open(ruta_imagen)
        ancho_original, alto_original = imagen.size

        ancho_escalado = ancho_original * factor_escala
        alto_escalado = alto_original * factor_escala

        canvas.drawImage(ruta_imagen, x, y, width=ancho_escalado, height=alto_escalado)

    # Cargar archivo de espesores
    archivo_xlsx_thickness = os.path.join(path_stats, 'aparc_stats_thickness_Z_score_robusto.xlsx')
    df_thickness_lh = pd.read_excel(archivo_xlsx_thickness, sheet_name='LH')
    df_thickness_rh = pd.read_excel(archivo_xlsx_thickness, sheet_name='RH')

    # Añadir una columna para identificar el hemisferio
    df_thickness_lh['Hemisferio'] = 'LH'
    df_thickness_rh['Hemisferio'] = 'RH'

    # Concatenar los DataFrames de ambos hemisferios
    df_thickness = pd.concat([df_thickness_lh, df_thickness_rh], ignore_index=True)


    # Dividir las regiones en los grupos especificados
    grupos_regiones = {
        'Espesores del Lóbulo Temporal': [
            'Bancos del surco temporal superior izquierdo', 'Bancos del surco temporal superior derecho', 
            'Entorrinal izquierdo', 'Entorrinal derecho', 
            'Fusiforme izquierdo', 'Fusiforme derecho', 
            'Temporal inferior izquierdo', 'Temporal inferior derecho', 
            'Temporal medio izquierdo', 'Temporal medio derecho', 
            'Parahipocampal izquierdo', 'Parahipocampal derecho', 
            'Temporal superior izquierdo', 'Temporal superior derecho', 
            'Polo temporal izquierdo', 'Polo temporal derecho', 
            'Temporal transverso izquierdo', 'Temporal transverso derecho'
        ],
        'Espesores del Lóbulo Parietal': [
            'Parietal inferior izquierdo', 'Parietal inferior derecho', 
            'Postcentral izquierdo', 'Postcentral derecho', 
            'Precuneo izquierdo', 'Precuneo derecho', 
            'Parietal superior izquierdo', 'Parietal superior derecho', 
            'Supramarginal izquierdo', 'Supramarginal derecho'
        ],
        'Espesores del Lóbulo Occipital': [
            'Cuneo izquierdo', 'Cuneo derecho', 
            'Occipital lateral izquierdo', 'Occipital lateral derecho', 
            'Lingual izquierdo', 'Lingual derecho', 
            'Pericalcarino izquierdo', 'Pericalcarino derecho'
        ],
        'Espesores del Lóbulo Frontal': [
            'Corteza frontal media caudal izquierda', 'Corteza frontal media caudal derecha', 
            'Polo frontal izquierdo', 'Polo frontal derecho', 
            'Orbitofrontal lateral izquierdo', 'Orbitofrontal lateral derecho', 
            'Orbitofrontal medial izquierdo', 'Orbitofrontal medial derecho', 
            'Paracentral izquierdo', 'Paracentral derecho', 
            'Pars opercularis izquierda', 'Pars opercularis derecha', 
            'Pars orbitalis izquierda', 'Pars orbitalis derecha', 
            'Pars triangularis izquierda', 'Pars triangularis derecha', 
            'Precentral izquierdo', 'Precentral derecho', 
            'Corteza frontal media rostral izquierda', 'Corteza frontal media rostral derecha', 
            'Frontal superior izquierdo', 'Frontal superior derecho'
        ],
        'Espesores del Lóbulo Cingulado': [
            'Corteza cingulada anterior caudal izquierda', 'Corteza cingulada anterior caudal derecha', 
            'Istmo cingulado izquierdo', 'Istmo cingulado derecho', 
            'Corteza cingulada posterior izquierda', 'Corteza cingulada posterior derecha', 
            'Corteza cingulada anterior rostral izquierda', 'Corteza cingulada anterior rostral derecha'
        ],
        'Espesores de Otras Regiones': [
            'Ínsula izquierda', 'Ínsula derecha', 
            'Espesor medio del hemisferio izquierdo', 'Espesor medio del hemisferio derecho'
        ]
    }



    # Agrupar los datos de IC_99%_Bajo y IC_99%_Alto en una sola columna
    df_thickness['Rango normal ajustado por edad según Z scores'] = df_thickness.apply(
        lambda row: f"{row['IC_99%_Bajo']} - {row['IC_99%_Alto']}", axis=1
    )

    # Reorganizar las columnas
    df_thickness = df_thickness[['Valor_Paciente_mm', 'Z_Score_Paciente', 'Rango normal ajustado por edad según Z scores', 'Dentro_de_Umbral_±3.5', 'Regiones_ESP']]

    # Asegurar el formato de dos decimales para todas las columnas numéricas
    df_thickness[['Valor_Paciente_mm', 'Z_Score_Paciente']] = df_thickness[['Valor_Paciente_mm', 'Z_Score_Paciente']].applymap(lambda x: f"{x:.2f}" if not pd.isna(x) else "0.00")


    df_thickness['Rango normal ajustado por edad según Z scores'] = df_thickness['Rango normal ajustado por edad según Z scores'].apply(formatear_rango_con_dos_decimales)

    #----------------------------------------------------------------------------------
    #Cargar el Excel con los datos de área
    archivo_xlsx_area = os.path.join(path_stats, 'aparc_stats_area_Z_score_robusto.xlsx')
    df_area_lh = pd.read_excel(archivo_xlsx_area, sheet_name='LH')
    df_area_rh = pd.read_excel(archivo_xlsx_area, sheet_name='RH')

    # Añadir una columna para identificar el hemisferio
    df_area_lh['Hemisferio'] = 'LH'
    df_area_rh['Hemisferio'] = 'RH'

    # Concatenar los DataFrames de ambos hemisferios
    df_area = pd.concat([df_area_lh, df_area_rh], ignore_index=True)

    # Agrupar los datos de IC_99%_Bajo y IC_99%_Alto en una sola columna
    df_area['Rango normal ajustado por edad según Z scores'] = df_area.apply(
        lambda row: f"{row['IC_99%_Bajo']} - {row['IC_99%_Alto']}", axis=1
    )

    # Reorganizar las columnas
    df_area = df_area[['Valor_Paciente_mm2', 'Z_Score_Paciente', 'Rango normal ajustado por edad según Z scores', 'Dentro_de_Umbral_±3.5', 'Regiones_ESP']]

    # Asegurar el formato de dos decimales para todas las columnas numéricas
    df_area[['Valor_Paciente_mm2', 'Z_Score_Paciente']] = df_area[['Valor_Paciente_mm2', 'Z_Score_Paciente']].applymap(lambda x: f"{x:.2f}" if not pd.isna(x) else "0.00")

    # Formatear la columna 'Rango normal ajustado por edad según Z scores'
    df_area['Rango normal ajustado por edad según Z scores'] = df_area['Rango normal ajustado por edad según Z scores'].apply(formatear_rango_con_dos_decimales)


    # Definición de los diccionarios de grupos de regiones
    grupos_regiones_area = {
        'Áreas del Lóbulo Temporal': [
            'Bancos del surco temporal superior izquierdo', 
            'Bancos del surco temporal superior derecho', 
            'Entorrinal izquierda', 
            'Entorrinal derecha', 
            'Fusiforme izquierda', 
            'Fusiforme derecha', 
            'Temporal inferior izquierda', 
            'Temporal inferior derecha', 
            'Temporal media izquierda', 
            'Temporal media derecha', 
            'Parahipocampal izquierda', 
            'Parahipocampal derecha', 
            'Temporal superior izquierda', 
            'Temporal superior derecha', 
            'Polo temporal izquierdo', 
            'Polo temporal derecho', 
            'Temporal transversa izquierda', 
            'Temporal transversa derecha'
        ],
        'Áreas del Lóbulo Parietal': [
            'Parietal inferior izquierda', 
            'Parietal inferior derecha', 
            'Postcentral izquierda', 
            'Postcentral derecha', 
            'Precuneo izquierdo', 
            'Precuneo derecho', 
            'Parietal superior izquierda', 
            'Parietal superior derecha', 
            'Supramarginal izquierda', 
            'Supramarginal derecha'
        ],
        'Áreas del Lóbulo Occipital': [
            'Cuneo izquierdo', 
            'Cuneo derecho', 
            'Occipital lateral izquierda', 
            'Occipital lateral derecha', 
            'Lingual izquierda', 
            'Lingual derecha', 
            'Pericalcarina izquierda', 
            'Pericalcarina derecha'
        ],
        'Áreas del Lóbulo Frontal': [
            'Corteza frontal media caudal izquierda', 
            'Corteza frontal media caudal derecha', 
            'Polo frontal izquierdo', 
            'Polo frontal derecho', 
            'Orbitofrontal lateral izquierda', 
            'Orbitofrontal lateral derecha', 
            'Orbitofrontal medial izquierda', 
            'Orbitofrontal medial derecha', 
            'Paracentral izquierda', 
            'Paracentral derecha', 
            'Pars opercularis izquierda', 
            'Pars opercularis derecha', 
            'Pars orbitalis izquierda', 
            'Pars orbitalis derecha', 
            'Pars triangularis izquierda', 
            'Pars triangularis derecha', 
            'Precentral izquierda', 
            'Precentral derecha', 
            'Corteza frontal media rostral izquierda', 
            'Corteza frontal media rostral derecha', 
            'Frontal superior izquierda', 
            'Frontal superior derecha'
        ],
        'Áreas del Lóbulo Cingulado': [
            'Corteza cingulada anterior caudal izquierda', 
            'Corteza cingulada anterior caudal derecha', 
            'Istmo cingulado izquierdo', 
            'Istmo cingulado derecho', 
            'Corteza cingulada posterior izquierda', 
            'Corteza cingulada posterior derecha', 
            'Corteza cingulada anterior rostral izquierda', 
            'Corteza cingulada anterior rostral derecha'
        ],
        'Áreas de Otras Regiones': [
            'Ínsula izquierda', 
            'Ínsula derecha', 
            'Superficie de sustancia blanca izquierda', 
            'Superficie de sustancia blanca derecha'
        ]
    }


    #----------------------------------------------------------------------------------
    #Cargar el Excel con los datos de foldind
    archivo_xlsx_foldind = os.path.join(path_stats, 'aparc_stats_foldind_Z_score_robusto.xlsx')
    df_foldind_lh = pd.read_excel(archivo_xlsx_foldind, sheet_name='LH')
    df_foldind_rh = pd.read_excel(archivo_xlsx_foldind, sheet_name='RH')

    # Añadir una columna para identificar el hemisferio
    df_foldind_lh['Hemisferio'] = 'LH'
    df_foldind_rh['Hemisferio'] = 'RH'

    # Concatenar los DataFrames de ambos hemisferios
    df_foldind = pd.concat([df_foldind_lh, df_foldind_rh], ignore_index=True)

    # Agrupar los datos de IC_99%_Bajo y IC_99%_Alto en una sola columna
    df_foldind['Rango normal ajustado por edad según Z scores'] = df_foldind.apply(
        lambda row: f"{row['IC_99%_Bajo']} - {row['IC_99%_Alto']}", axis=1
    )

    # Reorganizar las columnas
    df_foldind = df_foldind[['Valor_Paciente', 'Z_Score_Paciente', 'Rango normal ajustado por edad según Z scores', 'Dentro_de_Umbral_±3.5', 'Regiones_ESP']]

    # Asegurar el formato de dos decimales para todas las columnas numéricas
    df_foldind[['Valor_Paciente', 'Z_Score_Paciente']] = df_foldind[['Valor_Paciente', 'Z_Score_Paciente']].applymap(lambda x: f"{x:.2f}" if not pd.isna(x) else "0.00")

    # Formatear la columna 'Rango normal ajustado por edad según Z scores'
    df_foldind['Rango normal ajustado por edad según Z scores'] = df_foldind['Rango normal ajustado por edad según Z scores'].apply(formatear_rango_con_dos_decimales)


    # Definición del diccionario de regiones
    grupos_regiones_foldind = {
        'Índices del Lóbulo Temporal': [
            'Entorrinal izquierdo', 'Entorrinal derecho', 
            'Fusiforme izquierdo', 'Fusiforme derecho', 
            'Temporal inferior izquierdo', 'Temporal inferior derecho', 
            'Temporal medio izquierdo', 'Temporal medio derecho', 
            'Parahipocampal izquierdo', 'Parahipocampal derecho', 
            'Temporal superior izquierdo', 'Temporal superior derecho', 
            'Polo temporal izquierdo', 'Polo temporal derecho', 
            'Temporal transverso izquierdo', 'Temporal transverso derecho'
        ],
        'Índices del Lóbulo Parietal': [
            'Parietal inferior izquierdo', 'Parietal inferior derecho', 
            'Postcentral izquierdo', 'Postcentral derecho', 
            'Precuneo izquierdo', 'Precuneo derecho', 
            'Parietal superior izquierdo', 'Parietal superior derecho', 
            'Supramarginal izquierdo', 'Supramarginal derecho'
        ],
        'Índices del Lóbulo Occipital': [
            'Cuneo izquierdo', 'Cuneo derecho', 
            'Occipital lateral izquierdo', 'Occipital lateral derecho', 
            'Lingual izquierdo', 'Lingual derecho', 
            'Pericalcarino izquierdo', 'Pericalcarino derecho'
        ],
        'Índices del Lóbulo Frontal': [
            'Corteza frontal media caudal izquierda', 'Corteza frontal media caudal derecha', 
            'Polo frontal izquierdo', 'Polo frontal derecho', 
            'Orbitofrontal lateral izquierdo', 'Orbitofrontal lateral derecho', 
            'Orbitofrontal medial izquierdo', 'Orbitofrontal medial derecho', 
            'Paracentral izquierdo', 'Paracentral derecho', 
            'Pars opercularis izquierda', 'Pars opercularis derecha', 
            'Pars orbitalis izquierda', 'Pars orbitalis derecha', 
            'Pars triangularis izquierda', 'Pars triangularis derecha', 
            'Precentral izquierdo', 'Precentral derecho', 
            'Corteza frontal media rostral izquierda', 'Corteza frontal media rostral derecha', 
            'Frontal superior izquierdo', 'Frontal superior derecho'
        ],
        'Índices del Lóbulo Cingulado': [
            'Corteza cingulada anterior caudal izquierda', 'Corteza cingulada anterior caudal derecha', 
            'Istmo cingulado izquierdo', 'Istmo cingulado derecho', 
            'Corteza cingulada posterior izquierda', 'Corteza cingulada posterior derecha', 
            'Corteza cingulada anterior rostral izquierda', 'Corteza cingulada anterior rostral derecha'
        ],
        'Índices de Otras Regiones': [
            'Ínsula izquierda', 'Ínsula derecha'
        ]
    }

    path_csv_limbic = os.path.join(dicom_dir, "sclimbic_volumes_all.csv")
    df_sclimbic = pd.read_csv(path_csv_limbic)

    traducciones_regiones_limbic = {
    "Left-Nucleus-Accumbens": "Núcleo Accumbens Izquierdo",
    "Right-Nucleus-Accumbens": "Núcleo Accumbens Derecho",
    "Left-HypoThal-noMB": "Hipotálamo Izquierdo (sin Cuerpo Mamilar)",
    "Right-HypoThal-noMB": "Hipotálamo Derecho (sin Cuerpo Mamilar)",
    "Left-Fornix": "Fornix Izquierdo",
    "Right-Fornix": "Fornix Derecho",
    "Left-MammillaryBody": "Cuerpo Mamilar Izquierdo",
    "Right-MammillaryBody": "Cuerpo Mamilar Derecho",
    "Left-Basal-Forebrain": "Base del Prosencéfalo Izquierdo",
    "Right-Basal-Forebrain": "Base del Prosencéfalo Derecho",
    "Left-SeptalNuc": "Núcleo Septal Izquierdo",
    "Right-SeptalNuc": "Núcleo Septal Derecho"
    }



    # Cargar los datos de sclimbic (sclimbic_zqa_scores_all.csv and sclimbic_confidence_all.csv)
    path_csv_limbic_zqa_scores = os.path.join(dicom_dir, "sclimbic_zqa_scores_all.csv")
    df_sclimbic_zqa_scores = pd.read_csv(path_csv_limbic_zqa_scores)
    
    path_csv_limbic_confidences = os.path.join(dicom_dir, "sclimbic_confidences_all.csv")
    df_sclimbic_confidences = pd.read_csv(path_csv_limbic_confidences)

        
    traducciones_cerebelo = {
        "Left-Cerebellum-White-Matter": "Sustancia blanca del cerebelo izquierdo",
        "Right-Cerebellum-White-Matter": "Sustancia blanca del cerebelo derecho",
        "Left-Cerebellum-Cortex": "Corteza del cerebelo izquierdo",
        "Right-Cerebellum-Cortex": "Corteza del cerebelo derecho",
        "Cbm_Left_I_IV": "Cerebelo izquierdo lóbulos I–IV",
        "Cbm_Right_I_IV": "Cerebelo derecho lóbulos I–IV",
        "Cbm_Left_V": "Cerebelo izquierdo lóbulo V",
        "Cbm_Right_V": "Cerebelo derecho lóbulo V",
        "Cbm_Left_VI": "Cerebelo izquierdo lóbulo VI",
        "Cbm_Right_VI": "Cerebelo derecho lóbulo VI",
        "Cbm_Vermis_VI": "Vermis cerebeloso lóbulo VI",
        "Cbm_Left_CrusI": "Cerebelo izquierdo Crus I",
        "Cbm_Right_CrusI": "Cerebelo derecho Crus I",
        "Cbm_Left_CrusII": "Cerebelo izquierdo Crus II",
        "Cbm_Right_CrusII": "Cerebelo derecho Crus II",
        "Cbm_Left_VIIb": "Cerebelo izquierdo lóbulo VIIb",
        "Cbm_Right_VIIb": "Cerebelo derecho lóbulo VIIb",
        "Cbm_Left_VIIIa": "Cerebelo izquierdo lóbulo VIIIa",
        "Cbm_Right_VIIIa": "Cerebelo derecho lóbulo VIIIa",
        "Cbm_Left_VIIIb": "Cerebelo izquierdo lóbulo VIIIb",
        "Cbm_Right_VIIIb": "Cerebelo derecho lóbulo VIIIb",
        "Cbm_Left_IX": "Cerebelo izquierdo lóbulo IX",
        "Cbm_Right_IX": "Cerebelo derecho lóbulo IX",
        "Cbm_Vermis_IX": "Vermis cerebeloso lóbulo IX",
        "Cbm_Left_X": "Cerebelo izquierdo lóbulo X",
        "Cbm_Right_X": "Cerebelo derecho lóbulo X",
        "Cbm_Vermis_X": "Vermis cerebeloso lóbulo X",
        "Cbm_Vermis_VII": "Vermis cerebeloso lóbulo VII",
        "Cbm_Vermis_VIII": "Vermis cerebeloso lóbulo VIII",
        "Cbm_Vermis": "Vermis cerebeloso",
    }

    stats_path = os.path.join(path_stats, "cerebellum.CerebNet.stats")
    etiv_mm3 = float(df.loc[df["Measure:volume"]=="EstimatedTotalIntraCranialVol","Volumen_cm3"].iloc[0]) * 1000
    raw = (pd.read_csv(stats_path, comment="#", delim_whitespace=True, header=None,
                    names=["Index","SegId","NVoxels","Volume_mm3","StructName","normMean","normStdDev","normMin","normMax","normRange"])
        if os.path.exists(stats_path) else pd.DataFrame(columns=["StructName","Volume_mm3"]))
    df_cerebelo = (raw.assign(Estructura=raw["StructName"].map(traducciones_cerebelo).fillna(raw["StructName"]))
                    .reindex(columns=["Estructura","Volume_mm3"])
                    .rename(columns={"Volume_mm3":"Volumen_mm3"}))
    df_cerebelo["Volumen_relativo_%eTIV"] = df_cerebelo["Volumen_mm3"] / etiv_mm3 * 100






    #----------------------------------------------------------------------------------
    # Función para añadir contenido a una página específica
    def create_page_content(page_number):
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(template_dims[2], template_dims[3]))

        # Posiciones iniciales para la escritura de los datos
        x_position = 20
        x_position_region = 20
        x_position_volumen_cm3 = 270  # Ajusta estas posiciones según sea necesario
        x_position_volumen_vit = 383
        x_position_rango_normal = 490
        
        #----------- Texto ---------------
        # Define el estilo del párrafo
        estilo = styles.getSampleStyleSheet()["Normal"]
        estilo.fontName = "OpenSansLight"
        estilo.fontSize = 9
        estilo.leading = 14  # Ajusta el interlineado si es necesario
        estilo.textColor = (0.35, 0.35, 0.35)  # Color gris
        estilo.alignment = styles.TA_JUSTIFY  # Alineación justificada

        #----------------------------------------------------------------------------------  
        # Página 1

        if page_number == 0:
            # Configura la fuente y el color para el título
            can.setFont("OpenSansLight", 25)
            can.setFillColorRGB(0.45, 0.45, 0.45)  # Color gris  
            can.drawString(170, 815, "Reporte de Morfometría Cerebral")  # Ajusta estas coordenadas según sea necesario

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
            can.setFont("OpenSansLight", 10)
            can.setFillColorRGB(0.45, 0.45, 0.45)  # Ejemplo de color azul
            can.drawString(370, 665, "Espesor Cortical [mm]")
            can.drawString(345, 322, "Control de calidad de la segmentación")
            can.drawString(325, 531, "Perfil volumétrico: comparación con grupo control")


            # Rutas de las imágenes
            ruta_imagen_1 = os.path.join(path_surf, 'sag_thickness.png')
            ruta_imagen_2 = os.path.join(path_surf, 'cor_thickness.png')
            ruta_imagen_3 = os.path.join(path_surf, 'ax_thickness.png')
            ruta_imagen_4 = '/home/usuario/Bibliografia/pipeline_v2/recursos/colorbar_thickness.png'
            ruta_imagen_5 = os.path.join(path_mri, 'mask', 'control_de_calidad.png')
            ruta_imagen_6 = os.path.join(path_stats, 'comparac_control_pentagono.png')
            ruta_imagen_7 = os.path.join(path_stats, 'comparac_control_heatmap.png')
            ruta_imagen_8 = os.path.join(path_mri, 'mask', 'mesh.png')

            # Dibuja las imágenes con factores de escala diferentes (el primer parámetro ajusta posición en X y el 2do en Y)
            dibujar_imagen_escalada(can, ruta_imagen_1, 276, 560, factor_escala=0.25)  
            dibujar_imagen_escalada(can, ruta_imagen_2, 372, 560, factor_escala=0.25)  
            dibujar_imagen_escalada(can, ruta_imagen_3, 458, 555, factor_escala=0.25)  
            dibujar_imagen_escalada(can, ruta_imagen_4, 565, 555, factor_escala=0.19)  
            dibujar_imagen_escalada(can, ruta_imagen_5, 324, 59, factor_escala=0.11)  
            dibujar_imagen_escalada(can, ruta_imagen_6, 287, 375, factor_escala=0.075)
            dibujar_imagen_escalada(can, ruta_imagen_7, 455, 360, factor_escala=0.08)
            dibujar_imagen_escalada(can, ruta_imagen_8, 46, 96, factor_escala=0.1)


            
            # Texto de ejemplo
            texto_1 = """
            El análisis presentado en este reporte se llevó a cabo utilizando una imagen de alta resolución T1-w adquirida en un equipo de 3T.<br/><br/>
            Las mediciones de volumen se expresan en términos de valores absolutos (cm³) y como porcentaje del volumen intracraneal total (%VIT).
            """

            # Crea un objeto Paragraph con el texto y el estilo
            parrafo_1 = Paragraph(texto_1, estilo)

            # Dibuja el párrafo en el canvas
            # Ajusta x, y y ancho_max según sea necesario
            ancho_max = 220
            alto_max = 100
            parrafo_1.wrapOn(can, ancho_max, alto_max)
            parrafo_1.drawOn(can, 24, 673- alto_max)  # Ajusta x, y según sea necesario

            #----------- Texto 2---------------
            
            #texto_2 = """
            #El perfil volumétrico fue calculado mediante la comparación del volumen de regiones cerebrales específicas del sujeto con la mediana de los volúmenes correspondientes en un grupo control, el cual coincide con el género y rango etario del sujeto evaluado, garantizando una comparación adecuada y pertinente.<br/><br/>
            #Cabe destacar que los resultados mostrados en este perfil son únicamente a fines de obtener una perspectiva general sobre cómo el volumen cerebral del paciente se sitúa en relación con un estándar normativo y no deben interpretarse como análisis concluyentes. No se han realizado cálculos de significancia estadística en esta comparación y, por lo tanto, los datos proporcionados deben considerarse como una herramienta de referencia visual que puede ser útil para identificar tendencias o características particulares en las mediciones volumétricas del paciente.
            #"""
            #
            #    texto_2 = f"""
            #    El perfil volumétrico fue calculado mediante la comparación del volumen de regiones cerebrales específicas del sujeto con la mediana de los volúmenes correspondientes en un grupo control, el cual coincide con el género del sujeto evaluado. Sin embargo, debido a que el grupo control disponible incluye individuos con un rango etario de {rango_etario} años, mientras que el sujeto evaluado tiene {edad} años, esta diferencia de edad debe ser considerada al interpretar los resultados.<br/><br/>
            #    Cabe destacar que los resultados mostrados en este perfil son únicamente a fines de obtener una perspectiva general sobre cómo el volumen cerebral del paciente se sitúa en relación con un estándar normativo y no deben interpretarse como análisis concluyentes. No se han realizado cálculos de significancia estadística en esta comparación y, por lo tanto, los datos proporcionados deben considerarse como una herramienta de referencia visual.
            #    """
            def extraer_rango_etario(nombre_archivo):
                """
                Extrae el rango etario del nombre del archivo de la base de control.
                Ejemplo: 'grupo_18_29_masculino_aseg_stats_etiv_IC_Bootstrap.xlsx' -> (18, 29)
                """
                match = re.search(r'grupo_(\d{2})_(\d{2})', nombre_archivo)
                if match:
                    return int(match.group(1)), int(match.group(2))
                else:
                    return None, None

            # Extraer edad del paciente en formato numérico
            edad_paciente = int(datos_paciente["Edad"])

            # Extraer el rango etario de la base de control seleccionada
            nombre_base_control = os.path.basename(base_control_path)
            rango_inicio, rango_fin = extraer_rango_etario(nombre_base_control)

            # Verificar si la edad está dentro del rango
            if rango_inicio <= edad_paciente <= rango_fin:
                texto_2 = """
                El perfil volumétrico fue calculado mediante la comparación del volumen de regiones cerebrales específicas del sujeto con la mediana de los volúmenes correspondientes en un grupo control, el cual coincide con el género y rango etario del sujeto evaluado, garantizando una comparación adecuada y pertinente.<br/><br/>
                Cabe destacar que los resultados mostrados en este perfil son únicamente a fines de obtener una perspectiva general sobre cómo el volumen cerebral del paciente se sitúa en relación con un estándar normativo y no deben interpretarse como análisis concluyentes. No se han realizado cálculos de significancia estadística en esta comparación y, por lo tanto, los datos proporcionados deben considerarse como una herramienta de referencia visual que puede ser útil para identificar tendencias o características particulares en las mediciones volumétricas del paciente.
                """
            else:
                rango_etario = f"{rango_inicio}-{rango_fin}"
                texto_2 = f"""
                El perfil volumétrico fue calculado mediante la comparación del volumen de regiones cerebrales específicas del sujeto con la mediana de los volúmenes correspondientes en un grupo control, el cual coincide con el género del sujeto evaluado. Sin embargo, debido a que el grupo control disponible incluye individuos con un rango etario de {rango_etario} años, mientras que el sujeto evaluado tiene {edad_paciente} años, esta diferencia de edad debe ser considerada al interpretar los resultados.<br/><br/>
                Cabe destacar que los resultados mostrados en este perfil son únicamente a fines de obtener una perspectiva general sobre cómo el volumen cerebral del paciente se sitúa en relación con un estándar normativo y no deben interpretarse como análisis concluyentes. No se han realizado cálculos de significancia estadística en esta comparación y, por lo tanto, los datos proporcionados deben considerarse como una herramienta de referencia visual.
                """        

            # Crea un objeto Paragraph con el texto y el estilo
            parrafo_2 = Paragraph(texto_2, estilo)

            # Dibuja el párrafo en el canvas
            # Ajusta x, y y ancho_max según sea necesario
            ancho_max = 220
            alto_max = 100
            parrafo_2.wrapOn(can, ancho_max, alto_max)
            parrafo_2.drawOn(can, 24, 357- alto_max)  # Ajusta x, y según sea necesario

            #----------- Texto 3---------------
            estilo.fontSize = 8
            estilo.leading = 10
            texto_3= """
            Vista 3D del mallado generado durante el proceso de reconstrucción cortical.
            """

            # Crea un objeto Paragraph con el texto y el estilo
            parrafo_3 = Paragraph(texto_3, estilo)

            # Dibuja el párrafo en el canvas
            # Ajusta x, y y ancho_max según sea necesario
            ancho_max = 160
            alto_max = 100
            parrafo_3.wrapOn(can, ancho_max, alto_max)
            parrafo_3.drawOn(can, 44, 159- alto_max)  # Ajusta x, y según sea necesario
            estilo.fontSize = 9 # Vuelve al tamaño de fuente estándar del documento
            estilo.leading = 14 # Vuelve al interlineado estándar del documento


    #----------------------------------------------------------------------------------  
    # Página 2

        # Función para centrar el texto en una columna
        def centrar_texto(canvas, texto, x_posicion_inicial, ancho_columna, y, fuente, tamano_fuente):
            ancho_texto = pdfmetrics.stringWidth(texto, fuente, tamano_fuente)
            x_centro = x_posicion_inicial + (ancho_columna - ancho_texto) / 2
            canvas.drawString(x_centro, y, texto)
        # Asumiendo que tienes las columnas con anchos definidos
        ancho_columna_volumen_cm3 = 100
        ancho_columna_volumen_vit = 100
        ancho_columna_rango_normal = 100


        if page_number == 1:
            y_position = 780
            x_position_region = 20
            x_position_volumen_cm3 = 233  # Ajusta estas posiciones según sea necesario
            x_position_volumen_vit = 345
            x_position_rango_normal = 470

            # Dibuja los encabezados de las columnas
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color 
            can.setFont("OpenSansRegular", 9)
            can.drawString(x_position_volumen_cm3 + 17, y_position + 24, "Volumen en cm³")
            can.setFont("OpenSansRegular", 9)  # Vuelve al tamaño de fuente normal
            can.drawString(x_position_volumen_vit + 13, y_position + 24, "Volumen en %VIT")
            can.drawString(x_position_rango_normal + 1 , y_position + 28, "Rango normal ajustado")
            can.drawString(x_position_rango_normal + 5, y_position + 17, "por edad según %VIT")
            can.setFont("OpenSansLight", 9)

            #y_position -= 17

            for categoria, datos in datos_organizados.items():
                if categoria != "Volumen de Áreas Corticales":
                    can.setFont("OpenSansRegular", 10)
                    can.setFillColorRGB(0, 0, 0)  # Color 
                    can.drawString(x_position_region, y_position, categoria)

                    # Vuelve a OpenSansLight para los datos
                    can.setFont("OpenSansLight", 9)
                    can.setFillColorRGB(0.2, 0.2, 0.2)  # Color 
                    y_position -= 17



                    for _, fila in datos.iterrows():
                        # Centrar el texto de las columnas y dibujar
                        centrar_texto(can, fila['Volumen_cm3'], x_position_volumen_cm3, ancho_columna_volumen_cm3, y_position, "OpenSansLight", 9)
                        centrar_texto(can, fila['Volumen_%VIT'], x_position_volumen_vit, ancho_columna_volumen_vit, y_position, "OpenSansLight", 9)
                        centrar_texto(can, fila['Rango_normal_ajustado_por_edad_según_%VIT'], x_position_rango_normal, ancho_columna_rango_normal, y_position, "OpenSansLight", 9)

                        can.drawString(x_position_region + 15, y_position, fila['Regiones_ESP'])

                        y_position -= 20
                        if y_position < 50:
                            # Maneja el cambio de página
                            can.showPage()
                            can.setFont("OpenSansLight", 9)
                            can.setFillColorRGB(0, 0, 0)
                            y_position = 750

                    y_position -= 10


    #----------------------------------------------------------------------------------  
    # Página 3
        elif page_number == 2:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            # Dibuja los encabezados de las columnas
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color 
            can.setFont("OpenSansRegular", 9)
            can.drawString(x_position_volumen_cm3 - 22, y_position + 24, "Volumen en cm³")
            can.setFont("OpenSansRegular", 9)  # Vuelve al tamaño de fuente normal
            can.drawString(x_position_volumen_vit - 27, y_position + 24, "Volumen en %VIT")
            can.drawString(x_position_rango_normal - 20, y_position + 28, "Rango normal ajustado")
            can.drawString(x_position_rango_normal - 15, y_position + 17, "por edad según %VIT")
            #-----Columnas para Asimetrias--------
            can.drawString(x_position_volumen_vit - 195, y_position - 160, "%")
            can.drawString(x_position_volumen_vit - 158, y_position - 160, "Rango normal")

            can.drawString(x_position_volumen_vit + 72, y_position - 160, "%")
            can.drawString(x_position_volumen_vit + 117, y_position - 160, "Rango normal")

            can.setFont("OpenSansLight", 9)

            if "Volumen de Áreas Corticales" in datos_organizados:
                datos = datos_organizados["Volumen de Áreas Corticales"]
                can.setFont("OpenSansRegular", 10)
                can.setFillColorRGB(0, 0, 0)  # Color 
                can.drawString(x_position_region, y_position, "Volumen de Áreas Corticales")
                # Vuelve a OpenSansLight para los datos
                can.setFont("OpenSansLight", 9)
                can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
                y_position -= 17

                for _, fila in datos.iterrows():
                    can.drawString(x_position_region + 15, y_position, fila['Regiones_ESP'])
                    can.drawString(x_position_volumen_cm3, y_position, f"{fila['Volumen_cm3']}")
                    can.drawString(x_position_volumen_vit, y_position, f"{fila['Volumen_%VIT']}")
                    can.drawString(x_position_rango_normal + 3, y_position, f"{fila['Rango_normal_ajustado_por_edad_según_%VIT']}")

                    y_position -= 20

                    if y_position < 50:
                        break
                    
            # Agregar datos de Asimetrias antes del aviso de aclaración
            y_position_asimetrias_left = y_position - 50  # Ajusta la posición según sea necesario
            y_position_asimetrias_right = y_position - 70  # Ajusta la posición según sea necesario
            x_position_right_column = x_position_rango_normal - 120  # Ajusta según sea necesario

            can.setFont("OpenSansRegular", 10)
            can.drawString(x_position_region, y_position_asimetrias_left + 35, "Asimetría Interhemisférica Porcentual")
            can.setFont("OpenSansLight", 9)
            y_position_asimetrias_left -= 20

            # Texto sobre asimetrias
            # Define el estilo del párrafo
            estilo = styles.getSampleStyleSheet()["Normal"]
            estilo.fontName = "OpenSansLight"
            estilo.fontSize = 9
            estilo.leading = 14  # Ajusta el interlineado si es necesario
            estilo.textColor = (0.35, 0.35, 0.35)  # Color gris
            estilo.alignment = styles.TA_JUSTIFY  # Alineación justificada
            texto_asimetrias = """Esta métrica se calculó determinando la diferencia de volúmenes entre estructuras homólogas de ambos hemisferios, dividida por el promedio de los volúmenes de estas estructuras, proporcionando una medida normalizada de la disparidad volumétrica relativa."""
            # Crea un objeto Paragraph con el texto y el estilo
            parrafo_asimetrias = Paragraph(texto_asimetrias, estilo)

            # Dibuja el párrafo en el canvas
            # Ajusta x, y y ancho_max según sea necesario
            ancho_max = 530
            alto_max = 100
            parrafo_asimetrias.wrapOn(can, ancho_max, alto_max)
            parrafo_asimetrias.drawOn(can, 32, 750- alto_max)  # Ajusta x, y según sea necesario


            # Definir las listas de regiones para los dos grupos
            grupo_izquierda = [
                "Ventrículo Lateral", "Ventrículo Inferior Lateral", "Corteza del Cerebelo",
                "Sustancia Blanca del Cerebelo", "Corteza Cerebral", "Sustancia Blanca Cerebral",
                "Plexo coroideo"
            ]

            grupo_derecha = [
                "Tálamo", "Caudado", "Putamen", "Pálido", "Área Accumbens", "Hipocampo", "Amígdala"
            ]


            for _, fila in df_asimetrias.iterrows():
                asimetria_val = float(fila['Asimetria'])  # Convertir a float
                rango_normal_aip = fila['Rango_normal_ajustado_por_edad_según_AIP']  # Obtener el rango normal ajustado
                if fila['Region'] in grupo_izquierda:
                    can.drawString(x_position_region + 15, y_position_asimetrias_left - 35, fila['Region'])
                    can.drawString(x_position_volumen_cm3 - 90, y_position_asimetrias_left - 35, f"{asimetria_val:.2f}")
                    can.drawString(x_position_volumen_cm3 - 40, y_position_asimetrias_left - 35, rango_normal_aip)
                    y_position_asimetrias_left -= 20
                elif fila['Region'] in grupo_derecha:
                    can.drawString(x_position_right_column - 55, y_position_asimetrias_right - 35, fila['Region'])
                    can.drawString(x_position_right_column + 80, y_position_asimetrias_right - 35, f"{asimetria_val:.2f}")
                    can.drawString(x_position_right_column + 135, y_position_asimetrias_right - 35, rango_normal_aip)
                    y_position_asimetrias_right -= 20

            # Ajusta y_position para continuar con el contenido existente
            y_position = min(y_position_asimetrias_left, y_position_asimetrias_right)

    
            #-------------------Título de Morfometrías Corticales---------------------------------------
            can.setFont("OpenSansRegular", 12)
            can.setFillColorRGB(0, 0, 0)  # Color 
            can.drawString(x_position_region + 5, y_position - 215, "Morfometría Cortical")

            ruta_imagen_9 = f'{path_mri}/parcelacion_cortical.png'
            dibujar_imagen_escalada(can, ruta_imagen_9, 33, 176, factor_escala=0.40)

            #----------- Texto de aclaración ---------------
            can.setFont("OpenSansRegular", 9)
            can.drawString(x_position_volumen_vit - 350, y_position - 45, "Aclaración:")



            # Texto de ejemplo
            texto_4 = """
            En vista de la naturaleza y las características específicas de la muestra poblacional, los rangos normales para los volúmenes y asimetrías se determinaron utilizando un enfoque estadístico que considera los valores contenidos en un intervalo de confianza del 99%, proporcionando así un rango que excluye los extremos más atípicos de la distribución. Para esto, se utilizaron las medianas de cada región y un método de bootstrap. Esta técnica de remuestreo permite una estimación más robusta y fiable de los intervalos de confianza, especialmente con tamaños de muestra acordes a los utilizados para el cálculo realizado en este reporte.<br/>Sin embargo, es importante enfatizar que estos rangos no deben interpretarse como definitivos. Asimismo, proporcionan un marco comparativo que puede ayudar a identificar tendencias o características particulares en las mediciones volumétricas del paciente, dentro de un margen de variabilidad e incertidumbre inherente a la distribución de la muestra.
            """

            # Crea un objeto Paragraph con el texto y el estilo
            parrafo_4 = Paragraph(texto_4, estilo)

            # Dibuja el párrafo en el canvas
            # Ajusta x, y y ancho_max según sea necesario
            ancho_max = 530
            alto_max = 100
            parrafo_4.wrapOn(can, ancho_max, alto_max)
            parrafo_4.drawOn(can, 32, 425- alto_max)  # Ajusta x, y según sea necesario


            # Texto sobre morfolofía cortical
            can.setFont("OpenSansRegular", 9)
            can.drawString(x_position_volumen_vit - 351, y_position -345, "Las imágenes de parcelación cortical muestran las diferentes regiones anatómicas evaluadas.")
            texto_5 = """
            Las mediciones de espesor cortical se expresan en términos de valores absolutos (mm) y se comparan con una base de datos control. Para esta comparación, se calculó el score Z de cada región cortical en cada sujeto del grupo control. Con estos valores, se estableció un intervalo de confianza del 99% (IC 99%) para definir el rango normal de espesores corticales en el grupo control, asegurando que los datos sean representativos para sujetos del mismo género y rango etario. Adicionalmente, se realizó el mismo procedimiento para las mediciones de área cortical (mm²) e índice de plegamiento (Folding Index).<br/> 
            A continuación, se presentan los datos específicos del sujeto en comparación con los valores normativos obtenidos del grupo control, proporcionando una perspectiva detallada y cuantitativa de su perfil cortical.
            """

            # Crea un objeto Paragraph con el segundo texto y el estilo
            parrafo_5 = Paragraph(texto_5, estilo)

            # Dibuja el segundo párrafo en el canvas
            # Ajusta x, y y ancho_max según sea necesario
            alto_max_2 = 100
            parrafo_5.wrapOn(can, ancho_max, alto_max_2)
            parrafo_5.drawOn(can, 32, 145 - alto_max_2)  # Ajusta x, y según sea necesario



    #----------------------------------------------------------------------------------  
    # Página 4

        elif page_number == 3:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780
            #-------------------Título---------------------------------------
            can.setFont("OpenSansRegular", 12)
            can.setFillColorRGB(0, 0, 0)  # Color 
            can.drawString(x_position_region, y_position, "Espesores Corticales")

            # Configurar encabezados de columnas para espesores corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(323, y_position + 24, "mm")
            can.drawString(364, y_position + 24, "Z score")
            can.drawString(417, y_position + 30, "Rango normal ajustado")
            can.drawString(415, y_position + 19, "por edad según Z scores")
            can.drawString(537, y_position + 30, "Umbral")
            can.drawString(530, y_position + 19, "Z score ±3.5")
            can.setFont("OpenSansLight", 9)

            # Ajustar posiciones de columnas
            x_position_valor_paciente = 323
            x_position_z_score = 368
            x_position_rango_normal = 440
            x_position_umbral = 550

            y_position -= 10

            # Procesar los grupos de regiones
            for grupo, regiones in grupos_regiones.items():
                if grupo == 'Espesores del Lóbulo Cingulado':
                    continue  # Saltar este grupo para escribirlo en la página 5
                can.setFont("OpenSansRegular", 10)
                can.setFillColorRGB(0, 0, 0)  # Color
                can.drawString(20, y_position - 17, grupo)

                can.setFont("OpenSansLight", 9)
                can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
                y_position -= 25

                for region in regiones:
                    datos = df_thickness[df_thickness['Regiones_ESP'] == region]
                    for _, fila in datos.iterrows():
                        can.drawString(35, y_position - 17, str(fila['Regiones_ESP']))
                        valor_paciente_mm = f"{float(fila['Valor_Paciente_mm']):.2f}" if not pd.isna(fila['Valor_Paciente_mm']) else "0.00"
                        z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                        rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])

                        can.drawString(x_position_valor_paciente, y_position - 17, valor_paciente_mm)
                        can.drawString(x_position_z_score, y_position - 17, z_score_paciente)
                        can.drawString(x_position_rango_normal, y_position - 17, rango_normal)

                        can.setFont("ArialUnicode", 9)
                        dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                        can.drawString(x_position_umbral, y_position - 17, dentro_de_umbral)
                        can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                        y_position -= 20

                        if y_position < 50:
                            can.showPage()
                            can.setFont("OpenSansLight", 9)
                            can.setFillColorRGB(0, 0, 0)
                            y_position = 750

                y_position -= 10



    #----------------------------------------------------------------------------------  
    #----------------------------------------------------------------------------------  
    # Página 5

        elif page_number == 4:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 750

            # Configurar encabezados de columnas para espesores corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(323, y_position + 24, "mm")
            can.drawString(364, y_position + 24, "Z score")
            can.drawString(417, y_position + 30, "Rango normal ajustado")
            can.drawString(415, y_position + 19, "por edad según Z scores")
            can.drawString(537, y_position + 30, "Umbral")
            can.drawString(530, y_position + 19, "Z score ±3.5")
            can.setFont("OpenSansLight", 9)

            # Ajustar posiciones de columnas
            x_position_valor_paciente = 323
            x_position_z_score = 368
            x_position_rango_normal = 440
            x_position_umbral = 550

            # Mostrar el Lóbulo Frontal completo
            grupo = 'Espesores del Lóbulo Frontal'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 35

            for region in grupos_regiones[grupo]:
                datos = df_thickness[df_thickness['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position, str(fila['Regiones_ESP']))

                    valor_paciente_mm = f"{float(fila['Valor_Paciente_mm']):.2f}" if not pd.isna(fila['Valor_Paciente_mm']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position, valor_paciente_mm)
                    can.drawString(x_position_z_score, y_position, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position, rango_normal)
                    #can.drawString(x_position_umbral, y_position, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20

                    if y_position < 50:
                        can.showPage()
                        can.setFont("OpenSansLight", 9)
                        can.setFillColorRGB(0, 0, 0)
                        y_position = 750

            y_position -= 10  

            # Mostrar el Lóbulo Cingulado completo
            grupo = 'Espesores del Lóbulo Cingulado'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 19

            for region in grupos_regiones[grupo]:
                datos = df_thickness[df_thickness['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position, str(fila['Regiones_ESP']))

                    valor_paciente_mm = f"{float(fila['Valor_Paciente_mm']):.2f}" if not pd.isna(fila['Valor_Paciente_mm']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position, valor_paciente_mm)
                    can.drawString(x_position_z_score, y_position, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position, rango_normal)
                    #can.drawString(x_position_umbral, y_position, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20

                    if y_position < 20:
                        can.showPage()
                        can.setFont("OpenSansLight", 9)
                        can.setFillColorRGB(0, 0, 0)
                        y_position = 750

    #----------------------------------------------------------------------------------  
    # Página 6

        elif page_number == 5:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            # Configurar encabezados de columnas para áreas corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(323, y_position + 24, "mm")
            can.drawString(364, y_position + 24, "Z score")
            can.drawString(417, y_position + 30, "Rango normal ajustado")
            can.drawString(415, y_position + 19, "por edad según Z scores")
            can.drawString(537, y_position + 30, "Umbral")
            can.drawString(530, y_position + 19, "Z score ±3.5")
            can.setFont("OpenSansLight", 9)

            # Ajustar posiciones de columnas
            x_position_valor_paciente = 323
            x_position_z_score = 368
            x_position_rango_normal = 440
            x_position_umbral = 550

            # Mostrar 'Otras Regiones'
            grupo = 'Espesores de Otras Regiones'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 17

            for region in grupos_regiones[grupo]:
                datos = df_thickness[df_thickness['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position, str(fila['Regiones_ESP']))

                    valor_paciente_mm = f"{float(fila['Valor_Paciente_mm']):.2f}" if not pd.isna(fila['Valor_Paciente_mm']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position, valor_paciente_mm)
                    can.drawString(x_position_z_score, y_position, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position, rango_normal)
                    #can.drawString(x_position_umbral, y_position, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20

                    if y_position < 50:
                        can.showPage()
                        can.setFont("OpenSansLight", 9)
                        can.setFillColorRGB(0, 0, 0)
                        y_position = 750

            y_position -= 10  
    

            ruta_imagen_10 = f'{path_stats}/aparc_stats_thickness_Z_score_robusto_plots.png'
            dibujar_imagen_escalada(can, ruta_imagen_10, 25, 70, factor_escala=0.13)


    #----------------------------------------------------------------------------------  
    # Página 7

        elif page_number == 6:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            #------------------------------------------------------------------------------------
            #Escribir los datos de Áreas corticales
            #-------------------Título---------------------------------------
            can.setFont("OpenSansRegular", 12)
            can.setFillColorRGB(0, 0, 0)  # Color 
            can.drawString(x_position_region, y_position, "Áreas Corticales")

            # Configurar encabezados de columnas para espesores corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(323, y_position + 24, "mm²")
            can.drawString(364, y_position + 24, "Z score")
            can.drawString(417, y_position + 30, "Rango normal ajustado")
            can.drawString(415, y_position + 19, "por edad según Z scores")
            can.drawString(537, y_position + 30, "Umbral")
            can.drawString(530, y_position + 19, "Z score ±3.5")
            can.setFont("OpenSansLight", 9)

            # Ajustar posiciones de columnas
            x_position_valor_paciente = 323
            x_position_z_score = 368
            x_position_rango_normal = 440
            x_position_umbral = 550

            # Procesar los grupos de regiones de áreas
            for grupo, regiones in grupos_regiones_area.items():
                can.setFont("OpenSansRegular", 10)
                can.setFillColorRGB(0, 0, 0)  # Color negro
                can.drawString(20, y_position - 17, grupo)

                can.setFont("OpenSansLight", 9)
                can.setFillColorRGB(0.2, 0.2, 0.2)  # Color gris oscuro
                y_position -= 17

                for region in regiones:
                    datos = df_area[df_area['Regiones_ESP'] == region]
                    for _, fila in datos.iterrows():
                        can.drawString(35, y_position - 20, str(fila['Regiones_ESP']))
                        valor_paciente_mm2 = f"{float(fila['Valor_Paciente_mm2']):.0f}" if not pd.isna(fila['Valor_Paciente_mm2']) else "0.00"
                        z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                        rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                        dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                        can.drawString(x_position_valor_paciente, y_position - 20, valor_paciente_mm2)
                        can.drawString(x_position_z_score + 5, y_position - 20, z_score_paciente)
                        can.drawString(x_position_rango_normal, y_position - 20, rango_normal)
                        can.drawString(x_position_umbral, y_position - 20, dentro_de_umbral)

                        can.setFont("ArialUnicode", 9)
                        dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                        can.drawString(x_position_umbral, y_position - 20, dentro_de_umbral)
                        can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original
                        y_position -= 20

                        if y_position < 70:
                            can.showPage()
                            can.setFont("OpenSansLight", 9)
                            can.setFillColorRGB(0, 0, 0)
                            y_position = 750

                y_position -= 10


    #----------------------------------------------------------------------------------  
    # Página 8

        elif page_number == 7:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            # Configurar encabezados de columnas para espesores corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(324, y_position + 24, "mm²")
            can.drawString(364, y_position + 24, "Z score")
            can.drawString(417, y_position + 30, "Rango normal ajustado")
            can.drawString(415, y_position + 19, "por edad según Z scores")
            can.drawString(537, y_position + 30, "Umbral")
            can.drawString(530, y_position + 19, "Z score ±3.5")
            can.setFont("OpenSansLight", 9)

            # Ajustar posiciones de columnas
            x_position_valor_paciente = 323
            x_position_z_score = 368
            x_position_rango_normal = 440
            x_position_umbral = 550    


            # Mostrar todo el grupo 'Lóbulo Frontal'
            grupo = 'Áreas del Lóbulo Frontal'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 17

            for region in grupos_regiones_area[grupo]:
                datos = df_area[df_area['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position, str(fila['Regiones_ESP']))

                    valor_paciente_mm2 = f"{float(fila['Valor_Paciente_mm2']):.0f}" if not pd.isna(fila['Valor_Paciente_mm2']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position, valor_paciente_mm2)
                    can.drawString(x_position_z_score, y_position, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position, rango_normal)
                    #can.drawString(x_position_umbral, y_position, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20

            # Mostrar el grupo 'Áreas del Lóbulo Cingulado'
            grupo = 'Áreas del Lóbulo Cingulado'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position - 10, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 17

            for region in grupos_regiones_area[grupo]:
                datos = df_area[df_area['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position - 10, str(fila['Regiones_ESP']))

                    valor_paciente_mm2 = f"{float(fila['Valor_Paciente_mm2']):.0f}" if not pd.isna(fila['Valor_Paciente_mm2']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position - 10, valor_paciente_mm2)
                    can.drawString(x_position_z_score, y_position - 10, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position - 10, rango_normal)
                    #can.drawString(x_position_umbral, y_position, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position - 10, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20



    #----------------------------------------------------------------------------------  
    # Página 9

        elif page_number == 8:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            # Configurar encabezados de columnas para espesores corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(325, y_position + 24, "mm²")
            can.drawString(364, y_position + 24, "Z score")
            can.drawString(417, y_position + 30, "Rango normal ajustado")
            can.drawString(415, y_position + 19, "por edad según Z scores")
            can.drawString(537, y_position + 30, "Umbral")
            can.drawString(530, y_position + 19, "Z score ±3.5")
            can.setFont("OpenSansLight", 9)

            # Ajustar posiciones de columnas
            x_position_valor_paciente = 323
            x_position_z_score = 368
            x_position_rango_normal = 440
            x_position_umbral = 550

            # Mostrar el grupo 'Otras Regiones'
            grupo = 'Áreas de Otras Regiones'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 17

            for region in grupos_regiones_area[grupo]:
                datos = df_area[df_area['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position, str(fila['Regiones_ESP']))

                    valor_paciente_mm2 = f"{float(fila['Valor_Paciente_mm2']):.0f}" if not pd.isna(fila['Valor_Paciente_mm2']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position, valor_paciente_mm2)
                    can.drawString(x_position_z_score, y_position, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position, rango_normal)
                    #can.drawString(x_position_umbral, y_position, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20

            ruta_imagen_10 = f'{path_stats}/aparc_stats_area_Z_score_robusto_plots.png'
            dibujar_imagen_escalada(can, ruta_imagen_10, 25, 70, factor_escala=0.13)

    #----------------------------------------------------------------------------------  
    # Página 10

        elif page_number == 9:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            # Configurar encabezados de columnas para espesores corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(314, y_position + 30, "Folding")
            can.drawString(317, y_position + 19, "Index")
            can.drawString(365, y_position + 24, "Z score")
            can.drawString(417, y_position + 30, "Rango normal ajustado")
            can.drawString(415, y_position + 19, "por edad según Z scores")
            can.drawString(537, y_position + 30, "Umbral")
            can.drawString(530, y_position + 19, "Z score ±3.5")
            can.setFont("OpenSansLight", 9)

            # Ajustar posiciones de columnas
            x_position_valor_paciente = 323
            x_position_z_score = 368
            x_position_rango_normal = 440
            x_position_umbral = 550    

            #------------------------------------------------------------------------------------
            #------------------------------------------------------------------------------------
            #Escribir los datos de Índice de Plegamiento
            #-------------------Título---------------------------------------
            can.setFont("OpenSansRegular", 12)
            can.setFillColorRGB(0, 0, 0)  # Color 
            can.drawString(x_position_region, y_position, "Índices de Plegamiento")



            #x_position_valor_paciente_area = 310 #ajustar este valor para la localización de los datos de area (mm2)

            # Escribir los grupos de regiones de foldind
            for grupo, regiones in grupos_regiones_foldind.items():
                can.setFont("OpenSansRegular", 10)
                can.setFillColorRGB(0, 0, 0)  # Color negro
                can.drawString(20, y_position - 17, grupo)

                can.setFont("OpenSansLight", 9)
                can.setFillColorRGB(0.2, 0.2, 0.2)  # Color gris oscuro
                y_position -= 25

                for region in regiones:
                    datos = df_foldind[df_foldind['Regiones_ESP'] == region]
                    for _, fila in datos.iterrows():
                        can.drawString(35, y_position - 20, str(fila['Regiones_ESP']))
                        valor_paciente = f"{float(fila['Valor_Paciente']):.0f}" if not pd.isna(fila['Valor_Paciente']) else "0.00"
                        z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                        rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                        dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                        can.drawString(x_position_valor_paciente, y_position - 20, valor_paciente)
                        can.drawString(x_position_z_score + 5, y_position - 20, z_score_paciente)
                        can.drawString(x_position_rango_normal, y_position - 20, rango_normal)
                        can.drawString(x_position_umbral, y_position - 20, dentro_de_umbral)

                        can.setFont("ArialUnicode", 9)
                        dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                        can.drawString(x_position_umbral, y_position - 20, dentro_de_umbral)
                        can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original
                        y_position -= 20

                        if y_position < 60:
                            can.showPage()
                            can.setFont("OpenSansLight", 9)
                            can.setFillColorRGB(0, 0, 0)
                            y_position = 750

                y_position -= 10
    #----------------------------------------------------------------------------------  
    # Página 11
        elif page_number == 10:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            # Configurar encabezados de columnas para espesores corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(314, y_position + 30, "Folding")
            can.drawString(317, y_position + 19, "Index")
            can.drawString(365, y_position + 24, "Z score")
            can.drawString(417, y_position + 30, "Rango normal ajustado")
            can.drawString(415, y_position + 19, "por edad según Z scores")
            can.drawString(537, y_position + 30, "Umbral")
            can.drawString(530, y_position + 19, "Z score ±3.5")
            can.setFont("OpenSansLight", 9)

            # Ajustar posiciones de columnas
            x_position_valor_paciente = 323
            x_position_z_score = 368
            x_position_rango_normal = 440
            x_position_umbral = 550

            # Mostrar el Lóbulo Frontal completo
            grupo = 'Índices del Lóbulo Frontal'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 17

            for region in grupos_regiones_foldind[grupo]:
                datos = df_foldind[df_foldind['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position, str(fila['Regiones_ESP']))

                    valor_paciente = f"{float(fila['Valor_Paciente']):.0f}" if not pd.isna(fila['Valor_Paciente']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position, valor_paciente)
                    can.drawString(x_position_z_score, y_position, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position, rango_normal)
                    #can.drawString(x_position_umbral, y_position, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20

            # Mostrar el Lóbulo Cingulado completo
            grupo = 'Índices del Lóbulo Cingulado'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 17

            for region in grupos_regiones_foldind[grupo]:
                datos = df_foldind[df_foldind['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position, str(fila['Regiones_ESP']))

                    valor_paciente = f"{float(fila['Valor_Paciente']):.0f}" if not pd.isna(fila['Valor_Paciente']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position, valor_paciente)
                    can.drawString(x_position_z_score, y_position, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position, rango_normal)
                    #can.drawString(x_position_umbral, y_position, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20

                    if y_position < 20:
                        can.showPage()
                        can.setFont("OpenSansLight", 9)
                        can.setFillColorRGB(0, 0, 0)
                        y_position = 750


            # Mostrar el grupo 'Otras Regiones'
            grupo = 'Índices de Otras Regiones'
            can.setFont("OpenSansRegular", 10)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position - 10, grupo)

            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 17

            for region in grupos_regiones_foldind[grupo]:
                datos = df_foldind[df_foldind['Regiones_ESP'] == region]
                for _, fila in datos.iterrows():
                    can.drawString(35, y_position - 10, str(fila['Regiones_ESP']))

                    valor_paciente = f"{float(fila['Valor_Paciente']):.0f}" if not pd.isna(fila['Valor_Paciente']) else "0.00"
                    z_score_paciente = f"{float(fila['Z_Score_Paciente']):.2f}" if not pd.isna(fila['Z_Score_Paciente']) else "0.00"
                    rango_normal = str(fila['Rango normal ajustado por edad según Z scores'])
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])

                    can.drawString(x_position_valor_paciente, y_position - 10, valor_paciente)
                    can.drawString(x_position_z_score, y_position - 10, z_score_paciente)
                    can.drawString(x_position_rango_normal, y_position - 10, rango_normal)
                    #can.drawString(x_position_umbral, y_position - 10, dentro_de_umbral)

                    can.setFont("ArialUnicode", 9)
                    dentro_de_umbral = str(fila['Dentro_de_Umbral_±3.5'])
                    can.drawString(x_position_umbral, y_position - 10, dentro_de_umbral)
                    can.setFont("OpenSansLight", 9)  # Vuelve a la fuente original

                    y_position -= 20
    #----------------------------------------------------------------------------------  
    # Página 12
        elif page_number == 11:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 780

            ruta_imagen_11 = f'{path_stats}/aparc_stats_foldind_Z_score_robusto_plots.png'
            dibujar_imagen_escalada(can, ruta_imagen_11, 25, 240, factor_escala=0.13) 


            # Texto Aclaración final
            # Define el estilo del párrafo
            estilo = styles.getSampleStyleSheet()["Normal"]
            estilo.fontName = "OpenSansLight"
            estilo.fontSize = 9
            estilo.leading = 14  # Ajusta el interlineado si es necesario
            estilo.textColor = (0.35, 0.35, 0.35)  # Color gris
            estilo.alignment = styles.TA_JUSTIFY  # Alineación justificada
            ancho_max_3 = 516
            alto_max_3 = 100
            can.setFont("OpenSansRegular", 9)
            texto_6 = """
            Los límites normales se determinaron utilizando métricas independientes consensuadas por la comunidad internacional de imágenes neurológicas. Estas son: el intervalo de confianza del 99% (IC 99%), el cual abarca el rango donde se espera que caigan el 99% de los datos de una población sana, y el umbral de ±3.5 en el Z score que se utiliza para identificar valores atípicos significativos. Es importante destacar que el hecho de que algunas regiones presenten intervalos de confianza que sobrepasen el umbral de ±3.5 es simplemente una representación de la variabilidad normal de esa región en la muestra control.
            """

            # Crea un objeto Paragraph con el segundo texto y el estilo
            parrafo_6 = Paragraph(texto_6, estilo)

            # Dibuja el segundo párrafo en el canvas
            # Ajusta x, y y ancho_max según sea necesario

            parrafo_6.wrapOn(can, ancho_max_3, alto_max_3)
            parrafo_6.drawOn(can, 32, 213 - alto_max_3)  # Ajusta x, y según sea necesario

    #-----------------------------------------------------------------------------------
    # Página 13

        elif page_number == 12:
            can.setFont("OpenSansRegular", 11)
            can.setFillColorRGB(0, 0, 0)
            y_position = 780
        
            # Título de la sección
            can.drawString(20, y_position, "Volúmenes de Estructuras Subcorticales Límbicas")
            y_position -= 30
        
            # Encabezados de la tabla
            can.setFont("OpenSansRegular", 9)
            can.setFillColorRGB(0.090, 0.329, 0.721)  # Azul, como en pág. 11
            can.drawString(35, y_position, "Estructura")
            can.drawString(273, y_position, "Volumen en mm³")
            can.drawString(390, y_position, "ZQA Score")
            can.drawString(478, y_position, "Confianza")
        
            y_position -= 20
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Texto gris oscuro
        
            for region_en in traducciones_regiones_limbic.keys():
                region_es = traducciones_regiones_limbic[region_en]
        
                volumen = df_sclimbic.at[0, region_en] if region_en in df_sclimbic.columns else "N/A"
                zqa_score = df_sclimbic_zqa_scores.at[0, region_en] if region_en in df_sclimbic_zqa_scores.columns else "N/A"
                confianza = df_sclimbic_confidences.at[0, region_en] if region_en in df_sclimbic_confidences.columns else "N/A"
        
                volumen_format = f"{float(volumen):.2f}" if volumen != "N/A" else volumen
                zqa_format = f"{float(zqa_score):.2f}" if zqa_score != "N/A" else zqa_score
                confianza_format = f"{float(confianza):.2f}" if confianza != "N/A" else confianza
        
                can.drawString(35, y_position, region_es)
                can.drawString(300, y_position, volumen_format)
                can.drawString(400, y_position, zqa_format)
                can.drawString(490, y_position, confianza_format)
        
                y_position -= 20
        
                if y_position < 50:
                    can.showPage()
                    y_position = 780
                    can.setFont("OpenSansRegular", 9)
                    can.setFillColorRGB(0.090, 0.329, 0.721)
                    can.drawString(35, y_position, "Estructura")
                    can.drawString(273, y_position, "Volumen en mm³")
                    can.drawString(385, y_position, "ZQA Score")
                    can.drawString(475, y_position, "Confianza")
                    y_position -= 20
                    can.setFont("OpenSansLight", 9)
                    can.setFillColorRGB(0.2, 0.2, 0.2)
        

            # Texto aclaratorio para volúmenes límbicos
            can.setFont("OpenSansRegular", 9)
            estilo_limbic = styles.getSampleStyleSheet()["Normal"]
            estilo_limbic.fontName = "OpenSansLight"
            estilo_limbic.fontSize = 9
            estilo_limbic.leading = 14
            estilo_limbic.textColor = (0.35, 0.35, 0.35)
            estilo_limbic.alignment = styles.TA_JUSTIFY

            texto_limbic = """
            Las estructuras límbicas subcorticales fueron segmentadas utilizando una herramienta basada en redes neuronales convolucionales tipo U-Net. Las métricas ZQA y confianza media proporcionadas son indicadores internos de calidad del modelo: la puntuación ZQA representa un puntaje Z comparado con los sujetos utilizados en el entrenamiento, mientras que la confianza es la probabilidad posterior media dentro de la etiqueta segmentada. Si la puntuación ZQA es muy alta o la confianza es muy baja, se recomienda realizar una inspección visual del caso. Estas métricas no deben interpretarse como desviaciones respecto de una población normal, ya que los datos utilizados para entrenar el modelo no fueron seleccionados con ese fin. Es posible que los volúmenes obtenidos sean sistemáticamente mayores o menores al promedio del conjunto de entrenamiento, lo cual es esperable y no necesariamente patológico.
            """

            parrafo_limbic = Paragraph(texto_limbic, estilo_limbic)
            parrafo_limbic.wrapOn(can, 516, 100)
            parrafo_limbic.drawOn(can, 32, 340)  # Ajusta la posición del texto

            # Insertar la imagen de estructuras subcorticales limbicas
            ruta_imagen_sclimbic = os.path.join(path_mri, 'sclimbic_3d.png')
            dibujar_imagen_escalada(can, ruta_imagen_sclimbic, 50, 200, factor_escala=0.38)

    #-----------------------------------------------------------------------------------
    # Página 14
    #-----------------------------------------------------------------------------------    
        elif page_number == 13:
            can.setFont("OpenSansLight", 9)
            can.setFillColorRGB(0, 0, 0)  # Color negro
            y_position = 750

            # Configurar encabezados de columnas para espesores corticales
            can.setFillColorRGB(0.09019607843137255, 0.32941176470588235, 0.7215686274509804)  # Color
            can.setFont("OpenSansRegular", 9)
            can.drawString(30, y_position , "Estructura")
            can.drawString(285, y_position , "Volumen mm³")
            can.drawString(435, y_position , "Volumen relativo (%eTIV)")


            # Ajustar posiciones de columnas
            x_position_volumen = 305
            x_position_vol_rel = 475

            # Mostrar el Lóbulo Frontal completo
            grupo = 'Volúmenes sub-segmentación del cerebelo'
            can.setFont("OpenSansRegular", 12)
            can.setFillColorRGB(0, 0, 0)  # Color
            can.drawString(20, y_position+40, grupo)

            can.setFont("OpenSansLight", 10)
            can.setFillColorRGB(0.2, 0.2, 0.2)  # Color
            y_position -= 20

            for _, fila in df_cerebelo.iterrows():
                    can.drawString(35, y_position, str(fila['Estructura']))

                    volumen = f"{float(fila['Volumen_mm3']):.0f}" if not pd.isna(fila['Volumen_mm3']) else "0.00"
                    vol_rel = f"{float(fila['Volumen_relativo_%eTIV']):.2f}" if not pd.isna(fila['Volumen_relativo_%eTIV']) else "0.00"

                    can.drawString(x_position_volumen, y_position, volumen)
                    can.drawString(x_position_vol_rel, y_position, vol_rel)

                    y_position -= 20
        
            # Insertar la imagen de la firma
            ruta_imagen_firma = '/home/usuario/Bibliografia/pipeline_v2/recursos/firma_suaviz.png'
            dibujar_imagen_escalada(can, ruta_imagen_firma, 20, 20, factor_escala=0.17)

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
    final_pdf_path_original = os.path.join(path_stats, 'Reporte_completo.pdf')
    with open(final_pdf_path_original, "wb") as outputStream:
        output.write(outputStream)

    # Imprimir la ruta del archivo original
    print(f"\nArchivo PDF original generado exitosamente en: {final_pdf_path_original}")

    # Crear la versión comprimida con un nombre diferente
    final_pdf_path_comprimido = os.path.join(path_stats, 'Reporte_completo_comprimido.pdf')
    comprimir_pdf(final_pdf_path_original, final_pdf_path_comprimido)

    # Imprimir la ruta del archivo comprimido
    print(f"\nArchivo PDF comprimido generado exitosamente en: {final_pdf_path_comprimido}")