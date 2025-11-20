import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Cargar los tres archivos CSV
file_path1 = "/home/mbudani/results/procesamiento/DICE/synthsegDICE/csv_promedio.csv" # Cambia esto con la ruta de tu primer archivo CSV
file_path2 = "/home/mbudani/results/procesamiento/DICE/clinicalDICE/csv_promedio.csv"   # Cambia esto con la ruta de tu segundo archivo CSV
file_path3 = "/home/mbudani/results/procesamiento/DICE/fastsurferDICE/csv_promedio.csv" # Cambia esto con la ruta de tu tercer archivo CSV

# Cargar los datos de los tres archivos CSV
data1 = pd.read_csv(file_path1)
data2 = pd.read_csv(file_path2)
data3 = pd.read_csv(file_path3)

# Añadir la columna 'Modelo' para identificar los diferentes modelos
data1['Modelo'] = 'SynthSeg'
data2['Modelo'] = 'Recon-all-Clinical'
data3['Modelo'] = 'FastSurfer'

# Concatenar los tres DataFrames
combined_data = pd.concat([data1, data2, data3], ignore_index=True)

# Crear el gráfico de cajas
plt.figure(figsize=(10, 6))

# Usar Seaborn para crear el gráfico de cajas
sns.boxplot(
    data=combined_data,
    x='Modelo',  # Eje X: Diferentes modelos
    y='DICE',    # Eje Y: Valores de DICE
    palette="Set2",  # Colores distintos para cada modelo
    meanprops={'color': 'black', 'linewidth': 2},  # Cambia el color y el grosor de la línea de la media
)

# Agregar título y etiquetas al gráfico
plt.title("DICE por modelo-promedios generales", fontsize=14)
plt.xlabel("Modelo", fontsize=10)
plt.ylabel("DICE", fontsize=12)

# Limitar el eje Y para eliminar los valores cercanos a 0
plt.ylim(0.2,1.2)

# Calcular la media para cada modelo y agregarla a la leyenda
legend_labels = []
for i, model in enumerate(combined_data['Modelo'].unique()):
    # Calcular la media del modelo
    mean_value = combined_data[combined_data['Modelo'] == model]['DICE'].median()
    
    # Extraer el color correspondiente al modelo de la paleta "Set2"
    model_color = sns.color_palette("Set2")[i]
    
    # Añadir el círculo y el texto con el valor de la media en la leyenda
    legend_labels.append(
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=model_color, markersize=8, label=f'{model}: DICE = {mean_value:.2f}')
    )

# Mostrar la leyenda con los círculos de colores y las medias
plt.legend(handles=legend_labels, loc='lower right', fontsize=15)

# Rotar las etiquetas del eje X para mejor legibilidad
plt.xticks(rotation=0)

# Ajustar el layout para que no se corten las etiquetas
plt.tight_layout()

# Guardar el gráfico en un archivo
output_path = "/home/mbudani/results/procesamiento/graficos/DICE_general.png"  # Cambia la ruta si lo deseas guardar en otro formato o ubicación
plt.savefig(output_path, dpi=300)

print(f"El gráfico se ha guardado en: {output_path}")
