import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# =========================
# Función para cargar y pivotear
# =========================
def load_and_pivot(file_map, metric, col_metric, col_struct, col_label, etiquetas=None):
    dfs = []
    for model_name, path in file_map.items():
        df = pd.read_csv(path)
        # Renombrar columnas para unificar
        df = df.rename(columns={col_struct: "Estructura", col_metric: metric, col_label: "Etiqueta"})
        
        # Filtrar por etiquetas si se pasa una lista
        if etiquetas is not None:
            df = df[df["Etiqueta"].isin(etiquetas)]
        
        df["Modelo"] = model_name
        dfs.append(df[["Etiqueta", "Estructura", "Modelo", metric]])
    
    combined = pd.concat(dfs, ignore_index=True)
    
    # Usar Estructura como índice pero mantener orden por etiqueta
    pivoted = combined.pivot(index="Estructura", columns="Modelo", values=metric)
    
    # Ordenar por media (descendente para DICE, ascendente para HD95)
    if  metric.lower() == "dice":
        pivoted = pivoted.loc[pivoted.mean(axis=1).sort_values(ascending=False).index]
    else:
        pivoted = pivoted.loc[pivoted.mean(axis=1).sort_values(ascending=True).index]
    
    return pivoted


# =========================
# Archivos de entrada
# =========================
files_dice = {
    "SynthSeg": "/home/mbudani/results/procesamiento/DICE/synthsegDICE/dice_to_synthseg_1_SynthSeg.csv",
    "FastSurfer": "/home/mbudani/results/procesamiento/DICE/fastsurferDICE/dice_1_fastsurfer.csv",
    "Recon-all Clinical": "/home/mbudani/results/procesamiento/DICE/clinicalDICE/dice_1_clinical.csv"
}

files_hd95 = {
    "SynthSeg": "/home/mbudani/results/procesamiento/HD95/synthseg/hd95_aparc.DKTatlas+aseg_toMODELgrid_v1.nii.csv",
    "FastSurfer": "/home/mbudani/results/procesamiento/HD95/fastsurfer/hd95_aparc.DKTatlas+aseg_toMODELgrid.nii.csv",
    "Recon-all Clinical": "/home/mbudani/results/procesamiento/HD95/clinical/hd95_aparc.DKTatlas+aseg_toMODELgrid.nii.csv"
}

# =========================
# Cargar datos
# =========================
# Para DICE
list_subcortex=[10,11,12,13,17,18,26,49,50,51,52,53,54,58]
list_cortex=[1002,1006,1007,1008,1012,1014,1028,1030,1035,2002,2006,2007,2008,2012,2014,2030,2035]
pivot_dice = load_and_pivot(
    files_dice,
    metric="DICE",
    col_metric="DICE",
    col_struct="Estructura",
    col_label="Etiqueta",
    etiquetas=list_subcortex
)
# Para HD95
pivot_hd95 = load_and_pivot(
    files_hd95,
    metric="HD95",
    col_metric="hd95_mm",
    col_struct="label_name",
    col_label="label_id",
    etiquetas=list_subcortex
)

# =========================
# Plot
# =========================

# =========================
# Heatmap DICE
# =========================
fig_dice, ax_dice = plt.subplots(figsize=(8, 10))
sns.heatmap(
    pivot_dice,
    annot=True,
    fmt=".3f",
    cmap="YlOrRd",
    cbar_kws={'label': 'DICE'},
    ax=ax_dice,
    linewidths=0.5,
    linecolor='gray'
)

# Resaltar el mejor valor por fila con un rectángulo
for y, row in enumerate(pivot_dice.values):
    #print(row)
    x = row.argmax()
    ax_dice.add_patch(plt.Rectangle((x, y), 1, 1, fill=False, edgecolor='black', lw=2))

ax_dice.set_title("DICE por estructura y modelo", fontsize=14)
ax_dice.set_xlabel("Modelo")
ax_dice.set_ylabel("Estructura")

plt.tight_layout()
output_path_dice = "/home/mbudani/results/procesamiento/graficos/heatmap_DICEsubcortex_especifico_sujeto1.png"
plt.savefig(output_path_dice, dpi=600)
plt.close(fig_dice)  # Cierra la figura para liberar memoria
print(f"El gráfico DICE se ha guardado en: {output_path_dice}")

# =========================
# Heatmap HD95
# =========================
fig_hd95, ax_hd95 = plt.subplots(figsize=(8, 10))
sns.heatmap(
    pivot_hd95,
    annot=True,
    fmt=".2f",
    cmap="YlGnBu_r", # invertido porque menor es mejor
    cbar_kws={'label': 'HD95 (mm)'},
    ax=ax_hd95,
    linewidths=0.5,
    linecolor='gray',
)

# Resaltar el mejor valor por fila con un rectángulo
for y, row in enumerate(pivot_hd95.values):
    # Para HD95 el mejor es el valor mínimo
    x = row.argmin()
    ax_hd95.add_patch(plt.Rectangle((x, y),1, 1, fill=False, edgecolor='red', lw=2))


ax_hd95.set_title("HD95 por estructura y modelo", fontsize=14)
ax_hd95.set_xlabel("Modelo")
ax_hd95.set_ylabel("Estructura")

plt.tight_layout()
output_path_hd95 = "/home/mbudani/results/procesamiento/graficos/heatmap_HD95subcortex_especifico_sujeto1.png"
plt.savefig(output_path_hd95, dpi=600)
plt.close(fig_hd95)
print(f"El gráfico HD95 se ha guardado en: {output_path_hd95}")