import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

def plot_tiempos_por_sujeto(df: pd.DataFrame, output_path: Path) -> None:
    """
    Genera gráfico de barras agrupadas en dos filas:
    - Cada grupo representa un sujeto.
    - Cada barra representa un modelo.
    - Etiquetas de tiempo sobre cada barra.
    - Promedio resaltado con color especial.
    """
    modelos = ["FreeSurfer", "FastSurfer", "Reconall-Clinical", "SynthSeg"]
    colores = {
    "FreeSurfer": "#1F77B4",   # azul profundo
    "FastSurfer": "#7EC8E3",   # azul claro
    "Reconall-Clinical": "#9467BD",      # violeta
    "SynthSeg": "#B0CFEF",      # verde pastel (opcional)
    "promedio": "#A9D18E"    # color especial para promedio
    }

    # Separar sujetos y promedio
    df_sujetos = df[df["sujeto"] != "promedio"].copy()
    df_promedio = df[df["sujeto"] == "promedio"].copy()

    # Dividir en dos filas
    df_top = df_sujetos.iloc[:8]
    df_bottom = pd.concat([df_sujetos.iloc[8:], df_promedio], ignore_index=True)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharey=True)
    grupos = [df_top, df_bottom]
    titulos = ["Sujetos 1–8", "Sujetos 9–15 + Promedio"]

    for ax, grupo, titulo in zip(axes, grupos, titulos):
        x = np.arange(len(grupo))
        width = 0.2

        for i, modelo in enumerate(modelos):
            valores = grupo[modelo].astype(float).to_numpy()
            offset = (i - 1.5) * width
            barras = ax.bar(x + offset, valores, width, label=modelo, color=colores[modelo])

            # Etiquetas de tiempo sobre cada barra
            for bar in barras:
                altura = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    altura + 0.05,
                    f"{altura:.2f}",
                    ha='center',
                    va='bottom',
                    fontsize=8
                )

        # Si hay promedio, resaltarlo
        if "promedio" in grupo["sujeto"].values:
            idx = grupo.index[grupo["sujeto"] == "promedio"][0]
            x_prom = x[idx]
            for i, modelo in enumerate(modelos):
                valor = float(df_promedio[modelo])
                offset = (i - 1.5) * width
                ax.bar(
                    x_prom + offset,
                    valor,
                    width,
                    color=colores["promedio"],
                    edgecolor="black"
                )
                ax.text(
                    x_prom + offset,
                    valor + 0.05,
                    f"{valor:.2f}",
                    ha='center',
                    va='bottom',
                    fontsize=8,
                    fontweight='bold'
                )

        ax.set_xticks(x)
        ax.set_xticklabels(grupo["sujeto"], rotation=0)
        ax.set_title(titulo)
        ax.set_ylabel("Tiempo (horas)")
        ax.grid(axis='y', linestyle='--', alpha=0.3)

    fig.suptitle("Tiempos de procesamiento por sujeto y modelo", fontsize=14)
    fig.legend(modelos, loc="upper center", bbox_to_anchor=(0.5, 0.95), ncol=4, frameon=False)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=600)
    plt.close()
    print(f"Gráfico guardado en: {output_path}")
# Datos
data = {
    "sujeto": [str(i) for i in range(1, 16)] + ["promedio"],
    "FreeSurfer": [2.879, 2.557, 2.747, 2.741, 2.457, 3.041, 3.139, 3.111, 2.807, 3.124, 3.263, 3.142, 3.438, 3.023, 2.88, 2.9566],
    "FastSurfer": [0.8997222222, 0.7652777778, 0.8213888889, 0.7133333333, 0.7166666667, 0.8236111111, 0.9194444444, 0.9866666667, 0.8333333333, 0.9286111111, 1.086666667, 0.8838888889, 1.016666667, 1.0675, 0.8533333333, 0.8877407407],
    "Reconall-Clinical": [1.615, 1.328055556, 1.284444444, 1.061388889, 1.073888889, 1.468611111, 1.696666667, 1.713055556, 1.381666667, 1.664722222, 2.068611111, 1.679444444, 2.366666667, 1.550555556, 1.361388889, 1.554277778],
    "SynthSeg": [0.03333333333]*15 + [0.03293703704]
}
df = pd.DataFrame(data)

# Ruta de salida
output_path = Path("/home/mbudani/results/procesamiento/graficos/tiempos_modelos_color2.png")

# Ejecutar
plot_tiempos_por_sujeto(df, output_path)