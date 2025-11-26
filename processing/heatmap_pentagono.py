import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Importar variables y funciones de otros módulos
from processing.volumetric_analysis import traducciones, pares_regiones, traduccion_regiones, seleccionar_base_control, truncar_numero

def seleccionar_base_control_txt(edad, genero):
    """
    Selecciona automáticamente la base de datos control en formato .txt según la edad y el género.
    """
    base_dir = "/home/usuario/Bibliografia/pipeline_v2/recursos/morfo_cerebral/volumen/"

    if edad <= 18:
        grupo = "18_29"
    elif edad <= 29:
        grupo = "18_29"
    elif edad <= 44:
        grupo = "30_44"
    elif edad <= 60:
        grupo = "45_60"
    else:
        grupo = "45_60"

    genero = "femenino" if genero.lower() == "f" else "masculino"
    archivo_base = f"grupo_{grupo}_{genero}_aseg_stats_etiv.txt"

    archivo_path = os.path.join(base_dir, archivo_base)
    
    if not os.path.exists(archivo_path):
        raise RuntimeError(f"No se encontró el archivo de base de control en: {archivo_path}")

    return archivo_path

def leer_datos(archivo, es_control=True):
    if es_control:
        return pd.read_csv(archivo, sep='\t')
    else:
        return pd.read_csv(archivo, header=None, names=['Measure:volume', 'Volumen'], sep='\t')



def obtener_nombres_sujetos(datos):
    patron_sujetos = re.compile(r'[mf]\d{3}')
    return [col for col in datos.columns if patron_sujetos.match(col)]

def calcular_mediana_por_region(datos, regiones, sujetos):
    medianas = {}
    print("\n➤ Medianas del Grupo Control")
    for region, subregiones in regiones.items():
        if region in ['Sustancia Blanca', 'Sustancia Gris']:
            mediana_region = datos.loc[datos['Measure:volume'].isin(subregiones), sujetos].median(axis=1).values[0]
        else:
            sumas_regionales = datos.loc[datos['Measure:volume'].isin(subregiones), sujetos].sum()
            mediana_region = sumas_regionales.median()

        medianas[region] = mediana_region
        print(f"{region}: {mediana_region:.4f}")
    return medianas



def calcular_volumenes_sujeto(datos):
    """
    Calcula los volúmenes de las regiones usando los mismos nombres y estructura de regiones.
    """
    volumenes = {}
    regiones = [
        'Left-Cerebellum-White-Matter', 'Left-Cerebellum-Cortex', 
        'Right-Cerebellum-White-Matter', 'Right-Cerebellum-Cortex', 
        'CC_Posterior', 'CC_Mid_Posterior', 'CC_Central', 
        'CC_Mid_Anterior', 'CC_Anterior', 
        'Left-Hippocampus', 'Right-Hippocampus', 
        'CerebralWhiteMatterVol', 'TotalGrayVol'
    ]
    
    for region in regiones:
        volumen_region = datos.loc[datos['Measure:volume'] == region, 'Volumen']
        volumenes[region] = float(volumen_region.values[0]) if not volumen_region.empty else 0.0

    # Calcular combinaciones de regiones
    volumenes['Cerebelo'] = sum(volumenes[r] for r in [
        'Left-Cerebellum-White-Matter', 'Left-Cerebellum-Cortex', 
        'Right-Cerebellum-White-Matter', 'Right-Cerebellum-Cortex'
    ])
    volumenes['Cuerpo Calloso'] = sum(volumenes[r] for r in [
        'CC_Posterior', 'CC_Mid_Posterior', 'CC_Central', 
        'CC_Mid_Anterior', 'CC_Anterior'
    ])
    volumenes['Hipocampo'] = volumenes['Left-Hippocampus'] + volumenes['Right-Hippocampus']
    volumenes['Sustancia Blanca'] = volumenes['CerebralWhiteMatterVol']
    volumenes['Sustancia Gris'] = volumenes['TotalGrayVol']

    print("\n➤ Medianas del Paciente")
    for region in ['Cerebelo', 'Cuerpo Calloso', 'Hipocampo', 'Sustancia Blanca', 'Sustancia Gris']:
        print(f"{region}: {volumenes[region]:.4f}")

    return {region: volumenes[region] for region in ['Cerebelo', 'Cuerpo Calloso', 'Hipocampo', 'Sustancia Blanca', 'Sustancia Gris']}

def normalizar_valores(volumenes_control, volumenes_sujeto):
    return {
        region: volumenes_sujeto[region] / volumenes_control[region] if volumenes_control[region] != 0 else 0
        for region in volumenes_control.keys()
    }

def dibujar_pentagono(volumenes_control, volumenes_sujeto, archivo_salida):
    labels = list(volumenes_control.keys())
    valores_normalizados = normalizar_valores(volumenes_control, volumenes_sujeto)

    num_vars = len(labels)
    angulos = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angulos = [a + np.pi/10 for a in angulos]
    angulos += angulos[:1]

    valores_control = [1] * (num_vars + 1)
    valores_externo = [1.3] * (num_vars + 1)
    valores_sujeto = [valores_normalizados[label] for label in labels] + [valores_normalizados[labels[0]]]

    with plt.style.context('default'):
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

        # Dibujar las líneas de referencia
        for label, angle in zip(labels, angulos[:-1]):
            ax.plot([angle, angle], [0, 1.3], color='white', linestyle='dotted', linewidth=2)
        
        # Mediana control y paciente
        ax.plot(angulos, valores_control, color='#8fce00', linewidth=5, label='Mediana Control')
        ax.plot(angulos, valores_externo, color='#dadddb', linewidth=3, linestyle='-') 
        ax.fill(angulos, valores_externo, color='white', alpha=1)
        ax.plot(angulos, valores_sujeto, color='#ffd966', linewidth=2, label='Paciente')
        ax.fill(angulos, valores_sujeto, color='#ffd966', alpha=0.15)

        # Personalización de ejes
        ax.yaxis.set_visible(False)
        ax.spines['polar'].set_visible(False)
        ax.set_xticks(angulos[:-1])
        ax.set_xticklabels([])

        # Alinear etiquetas del pentágono
        for label, angle in zip(labels, angulos[:-1]):
            ha = 'center' if label == 'Cuerpo Calloso' else ('right' if np.cos(angle) < 0 else 'left')
            va = 'bottom' if np.sin(angle) > 0 else 'top'
            ax.text(angle, 1.4, label, horizontalalignment=ha, verticalalignment=va, color='gray', fontsize=14)

        # Leyenda
        legend = plt.legend(loc='lower center', bbox_to_anchor=(0.5, -0.05))
        for text in legend.get_texts():
            text.set_color("gray")

        # Guardar la imagen
        fig.savefig(archivo_salida, dpi=300, bbox_inches='tight')
        plt.close()


def dibujar_heatmap(volumenes_control, volumenes_sujeto, categorias, archivo_salida_2):
    data = np.array([list(volumenes_control.values()), list(volumenes_sujeto.values())])

    with plt.style.context('default'):
        fig, ax = plt.subplots()
        sns.heatmap(data, annot=True, cmap='YlGnBu', xticklabels=categorias, yticklabels=['Control', 'Sujeto'], ax=ax, vmin=0, vmax=data.max())
        plt.title('%VIT', color='gray')

        for label in ax.get_xticklabels():
            label.set_color('gray')

        for label in ax.get_yticklabels():
            label.set_color('gray')

        fig.savefig(archivo_salida_2, dpi=300, bbox_inches='tight')
        #plt.show()

def generar_heatmap_pentagono(stats_folder, base_control_path):
    """
    Genera el heatmap y pentágono usando la base de control.
    """
    # Configuración de las regiones
    regiones = {
        'Cerebelo': ['Left-Cerebellum-White-Matter', 'Left-Cerebellum-Cortex', 'Right-Cerebellum-White-Matter', 'Right-Cerebellum-Cortex'],
        'Cuerpo Calloso': ['CC_Posterior', 'CC_Mid_Posterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Anterior'],
        'Hipocampo': ['Left-Hippocampus', 'Right-Hippocampus'],
        'Sustancia Blanca': ['CerebralWhiteMatterVol'],
        'Sustancia Gris': ['TotalGrayVol']
    }
    #print(f"Intentando leer archivo de control: {base_control_path}")
    # Leer datos del grupo control
    datos_control = leer_datos(base_control_path)
    sujetos_control = obtener_nombres_sujetos(datos_control)
    medianas_control = calcular_mediana_por_region(datos_control, regiones, sujetos_control)


    # Leer y procesar datos del sujeto
    archivo_sujeto = os.path.join(stats_folder, 'aseg_stats_etiv.txt')
    datos_sujeto = leer_datos(archivo_sujeto, es_control=False)
    volumenes_sujeto = calcular_volumenes_sujeto(datos_sujeto)

    # Dibujar el gráfico
    archivo_salida = f'{stats_folder}/comparac_control_pentagono.png'
    dibujar_pentagono(medianas_control, volumenes_sujeto, archivo_salida)
    
    # Dibujar el heatmap
    categorias = list(regiones.keys())
    archivo_salida_2 = f'{stats_folder}/comparac_control_heatmap.png'
    dibujar_heatmap(medianas_control, volumenes_sujeto, categorias, archivo_salida_2)

    print(f"\nGráficos guardados  en:\n{archivo_salida}\n{archivo_salida_2}")