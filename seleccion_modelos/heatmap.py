import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# =========================
# Función para cargar y pivotear
# =========================
def load_and_pivot(file_map, metric, col_metric, col_struct):
    dfs = []
    for model_name, path in file_map.items():
        df = pd.read_csv(path)
        # Renombrar columnas para unificar
        df = df.rename(columns={col_struct: "Estructura", col_metric: metric})
        df["Modelo"] = model_name
        dfs.append(df[["Estructura", "Modelo", metric]])
    combined = pd.concat(dfs, ignore_index=True)
    pivoted = combined.pivot(index="Estructura", columns="Modelo", values=metric)
    # Ordenar por media (descendente para DICE, ascendente para HD95)
    if metric.lower() == "dice":
        pivoted = pivoted.loc[pivoted.mean(axis=1).sort_values(ascending=False).index]
    else:
        pivoted = pivoted.loc[pivoted.mean(axis=1).sort_values(ascending=True).index]
    return pivoted

# =========================
# Función para crear máscara de resaltado del mejor valor
# =========================
def highlight_best(data, metric):
    mask = np.zeros_like(data, dtype=bool)
    if metric.lower() == "dice":
        best_idx = data.values.argmax(axis=1)
    else:  # HD95: menor es mejor
        best_idx = data.values.argmin(axis=1)
    for row, col in enumerate(best_idx):
        mask[row, col] = True
    return mask

# =========================
# Archivos de entrada
# =========================
files_dice = {
    "SynthSeg": "/home/mbudani/results/procesamiento/DICE/synthsegDICE/csv_promedio.csv",
    "FastSurfer": "/home/mbudani/results/procesamiento/DICE/fastsurferDICE/csv_promedio.csv",
    "Recon-all Clinical": "/home/mbudani/results/procesamiento/DICE/clinicalDICE/csv_promedio.csv"
}

files_hd95 = {
    "SynthSeg": "/home/mbudani/results/procesamiento/HD95/synthseg/csv_promedio.csv",
    "FastSurfer": "/home/mbudani/results/procesamiento/HD95/fastsurfer/csv_promedio.csv",
    "Recon-all Clinical": "/home/mbudani/results/procesamiento/HD95/clinical/csv_promedio.csv"
}

# =========================
# Cargar datos
# =========================
pivot_dice = load_and_pivot(files_dice, metric="DICE", col_metric="DICE", col_struct="Estructura")
pivot_hd95 = load_and_pivot(files_hd95, metric="HD95", col_metric="hd95_mm", col_struct="label_name")

# =========================
# Crear máscaras de resaltado
# =========================
mask_dice = highlight_best(pivot_dice, "DICE")
mask_hd95 = highlight_best(pivot_hd95, "HD95")

# =========================
# Plot
# =========================
sns

# =========================
# Heatmap DICE
# =========================
fig_dice, ax_dice = plt.subplots(figsize=(8, 10))
sns.heatmap(
    pivot_dice,
    annot=True,
    fmt=".3f",
    cmap="YlGnBu",
    cbar_kws={'label': 'DICE'},
    ax=ax_dice,
    linewidths=0.5,
    linecolor='gray'
)

# Resaltar el mejor valor por fila con un rectángulo
for y, row in enumerate(pivot_dice.values):
    if "dice" in "DICE".lower():
        x = row.argmax()
    else:
        x = row.argmin()
    ax_dice.add_patch(plt.Rectangle((x, y), 1, 1, fill=False, edgecolor='red', lw=2))

ax_dice.set_title("DICE por estructura y modelo", fontsize=14)
ax_dice.set_xlabel("Modelo")
ax_dice.set_ylabel("Estructura")

plt.tight_layout()
output_path_dice = "/home/mbudani/results/procesamiento/graficos/heatmap_DICE_general.png"
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
    cmap="YlOrRd_r",  # invertido porque menor es mejor
    cbar_kws={'label': 'HD95 (mm)'},
    ax=ax_hd95,
    linewidths=0.5,
    linecolor='gray',
)

# Resaltar el mejor valor por fila con un rectángulo
for y, row in enumerate(pivot_hd95.values):
    if "hd95" in "DICE".lower():
        x = row.argmax()
    else:
        x = row.argmin()
    ax_dice.add_patch(plt.Rectangle((x, y), 1, 1, fill=False, edgecolor='red', lw=2))


ax_hd95.set_title("HD95 por estructura y modelo", fontsize=14)
ax_hd95.set_xlabel("Modelo")
ax_hd95.set_ylabel("Estructura")

plt.tight_layout()
output_path_hd95 = "/home/mbudani/results/procesamiento/graficos/heatmap_HD95_general.png"
plt.savefig(output_path_hd95, dpi=600)
plt.close(fig_hd95)
print(f"El gráfico HD95 se ha guardado en: {output_path_hd95}")