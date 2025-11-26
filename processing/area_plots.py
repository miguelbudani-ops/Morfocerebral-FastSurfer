import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.lines as mlines
import re

# Configuración de estilo de gráficos
sns.set_theme(style="darkgrid")

def limpiar_nombre_region(region):
    """Limpia los nombres de las regiones para mejorar la visualización en el gráfico."""
    region = region.replace("medio del hemisferio izquierdo", "Área media del hemisferio izquierdo")
    region = region.replace("medio del hemisferio derecho", "Área media del hemisferio derecho")
    region = re.sub(r'^Área de los ', '', region)
    region = re.sub(r'^Área de la ', '', region)
    region = re.sub(r'^Área del ', '', region)
    region = re.sub(r'^Área ', '', region)
    region = re.sub(r'\bizquierda\b|\bizquierdo\b|\bderecha\b|\bderecho\b', '', region)
    return region.strip()

def graficar_areas(stats_folder):
    """
    Genera gráficos de dispersión de Z-score de áreas corticales con intervalos de confianza.
    """
    # Ruta al archivo Excel
    file_path = os.path.join(stats_folder, 'aparc_stats_area_Z_score_robusto.xlsx')

    # Cargar el archivo Excel
    df_lh = pd.read_excel(file_path, sheet_name='LH', engine='openpyxl')
    df_rh = pd.read_excel(file_path, sheet_name='RH', engine='openpyxl')

    # Seleccionar columnas de interés
    columns_of_interest = ['Z_Score_Paciente', 'IC_99%_Bajo', 'IC_99%_Alto', 'Regiones_ESP']
    df_lh_filtered = df_lh[columns_of_interest]
    df_rh_filtered = df_rh[columns_of_interest]

    # Limpiar los nombres de las regiones
    df_lh_filtered['Áreas'] = df_lh_filtered['Regiones_ESP'].apply(limpiar_nombre_region)
    df_rh_filtered['Áreas'] = df_rh_filtered['Regiones_ESP'].apply(limpiar_nombre_region)

    # Excluir "BrainSegVolNotVent" y "eTIV"
    df_lh_filtered = df_lh_filtered[~df_lh_filtered['Regiones_ESP'].isin(["Volumen segmentado del cerebro sin ventrículos", "Volumen intracraneal estimado"])]
    df_rh_filtered = df_rh_filtered[~df_rh_filtered['Regiones_ESP'].isin(["Volumen segmentado del cerebro sin ventrículos", "Volumen intracraneal estimado"])]

    # Crear subplots para los hemisferios izquierdo y derecho
    fig, axes = plt.subplots(2, 1, figsize=(14, 15))
    fig.patch.set_facecolor('#f8f8f8')  # Color de fondo de la figura

    for ax in axes:
        ax.set_facecolor('#efefef')  # Color de fondo del gráfico

    # Línea de umbral para la leyenda
    umbral_line = mlines.Line2D([], [], color='red', linestyle='-', label='Umbral ±3.5')

    # Gráfico del hemisferio izquierdo
    sns.scatterplot(ax=axes[0], x=df_lh_filtered['Áreas'], y=df_lh_filtered['Z_Score_Paciente'], label='Z Score Paciente', marker='X', color='gray')
    sns.lineplot(ax=axes[0], x=df_lh_filtered['Áreas'], y=df_lh_filtered['IC_99%_Bajo'], label='IC 99%', linestyle='--', color='#fcd15b')
    sns.lineplot(ax=axes[0], x=df_lh_filtered['Áreas'], y=df_lh_filtered['IC_99%_Alto'], linestyle='--', color='#fcd15b')
    axes[0].fill_between(df_lh_filtered['Áreas'], df_lh_filtered['IC_99%_Bajo'], df_lh_filtered['IC_99%_Alto'], color='#f2d483', alpha=0.1)
    axes[0].fill_between(df_lh_filtered['Áreas'], 3.5, 4, color='red', alpha=0.1)
    axes[0].fill_between(df_lh_filtered['Áreas'], -3.5, -4, color='red', alpha=0.1)
    axes[0].axhline(y=3.5, color='red', linestyle='--', linewidth=0.5)
    axes[0].axhline(y=-3.5, color='red', linestyle='--', linewidth=0.5)
    axes[0].set_title('Áreas Hemisferio Izquierdo')
    axes[0].set_ylabel('Z Score')
    axes[0].tick_params(axis='x', rotation=90)
    axes[0].legend(handles=axes[0].get_legend_handles_labels()[0] + [umbral_line], loc='upper right', bbox_to_anchor=(1, 1), facecolor='white', framealpha=0.9)

    # Gráfico del hemisferio derecho
    sns.scatterplot(ax=axes[1], x=df_rh_filtered['Áreas'], y=df_rh_filtered['Z_Score_Paciente'], label='Z Score Paciente', marker='X', color='gray')
    sns.lineplot(ax=axes[1], x=df_rh_filtered['Áreas'], y=df_rh_filtered['IC_99%_Bajo'], label='IC 99%', linestyle='--', color='#fcd15b')
    sns.lineplot(ax=axes[1], x=df_rh_filtered['Áreas'], y=df_rh_filtered['IC_99%_Alto'], linestyle='--', color='#fcd15b')
    axes[1].fill_between(df_rh_filtered['Áreas'], df_rh_filtered['IC_99%_Bajo'], df_rh_filtered['IC_99%_Alto'], color='#f2d483', alpha=0.1)
    axes[1].fill_between(df_rh_filtered['Áreas'], 3.5, 4, color='red', alpha=0.1)
    axes[1].fill_between(df_rh_filtered['Áreas'], -3.5, -4, color='red', alpha=0.1)
    axes[1].axhline(y=3.5, color='red', linestyle='--', linewidth=0.5)
    axes[1].axhline(y=-3.5, color='red', linestyle='--', linewidth=0.5)
    axes[1].set_title('Áreas Hemisferio Derecho')
    axes[1].set_ylabel('Z Score')
    axes[1].tick_params(axis='x', rotation=90)
    axes[1].legend().set_visible(False)

    # Personalizar el grid para conservar solo la línea horizontal en 0
    for ax in axes:
        ax.yaxis.grid(False)
        ax.xaxis.grid(True)
        ax.axhline(0, color='white', linewidth=0.5)

    # Eliminar el label 'Áreas' del gráfico
    axes[0].set_xlabel('')
    axes[1].set_xlabel('')

    # Mostrar y guardar el gráfico
    plt.tight_layout()
    output_image_path = os.path.join(stats_folder, 'aparc_stats_area_Z_score_robusto_plots.png')
    plt.savefig(output_image_path, dpi=300)
    #plt.show()
    print("")
    print(f"Gráficos guardados en: {output_image_path}")
    plt.close()
    
