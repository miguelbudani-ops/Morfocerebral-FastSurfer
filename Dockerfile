# ===============================================
# Morfometría: FastSurfer + FreeSurfer + FSL + utilidades
# Base root-only para simplificar permisos en /etc/* y installs
# ===============================================
FROM ubuntu:22.04

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ------------------------------------------------
# Paquetes del sistema
# ------------------------------------------------
RUN set -euxo pipefail && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates curl wget gnupg unzip zip git rsync \
      build-essential cmake ninja-build pkg-config \
      python3 python3-pip python3-dev \
      tcsh lsb-release sudo locales \
      xorg xvfb xauth x11-apps xdotool wmctrl openbox \
      libglu1-mesa libgl1 libglvnd0 libxrender1 libxtst6 libxcomposite1 libxss1 libxi6 libxrandr2 libxfixes3 libxdamage1 libxft2 \
      libsm6 libice6 libxcb1 libxkbcommon-x11-0 libdbus-1-3 \
      libgtk-3-0 libasound2 libnss3 libnspr4 libgbm1 libdrm2 fontconfig imagemagick \
      dcm2niix bc dc inotify-tools parallel \
      jq less vim \
      libmng2 libjpeg-turbo8 libopenblas-base libpng-dev \
      libsuitesparse-dev \
      ghostscript \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------
# Árbol de trabajo
# ------------------------------------------------
ENV HOME=/home/usuario
RUN mkdir -p /home/usuario/Bibliografia/pipeline_v2
WORKDIR /home/usuario

# Copias (root propietario; permisos de lectura para todos)
COPY FastSurfer   /home/usuario/FastSurfer
RUN find /home/usuario/FastSurfer -name '*.sh' -exec chmod +x {} +
COPY freesurfer   /home/usuario/Bibliografia/freesurfer
#COPY preprocessing /home/usuario/Bibliografia/pipeline_v2/preprocessing
#COPY processing    /home/usuario/Bibliografia/pipeline_v2/processing
#COPY recursos      /home/usuario/Bibliografia/pipeline_v2/recursos
#COPY main_local.py /home/usuario/Bibliografia/pipeline_v2/main_local.py
#RUN install -m 0644 -D /dev/null /home/usuario/Bibliografia/pipeline_v2/__init__.py

# ------------------------------------------------
# FreeSurfer
# ------------------------------------------------
ENV FREESURFER_HOME=/home/usuario/Bibliografia/freesurfer \
    FS_LICENSE=/home/usuario/Bibliografia/freesurfer/license.txt
RUN echo "source ${FREESURFER_HOME}/SetUpFreeSurfer.sh" > /etc/profile.d/freesurfer.sh && \
    chmod 0644 /etc/profile.d/freesurfer.sh

# ------------------------------------------------
# FSL
# ------------------------------------------------
RUN set -euxo pipefail && \
    wget -O /tmp/fslinstaller.py https://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py && \
    python3 /tmp/fslinstaller.py --dest=/home/usuario/fsl --quiet && \
    rm -f /tmp/fslinstaller.py
ENV FSLDIR=/home/usuario/fsl \
    FSLOUTPUTTYPE=NIFTI_GZ
RUN echo "FSLDIR=/home/usuario/fsl" > /etc/profile.d/fsl.sh && \
    echo ". \${FSLDIR}/etc/fslconf/fsl.sh" >> /etc/profile.d/fsl.sh && \
    echo "export FSLDIR FSLOUTPUTTYPE PATH" >> /etc/profile.d/fsl.sh && \
    chmod 0644 /etc/profile.d/fsl.sh

# ------------------------------------------------
# Miniconda + mamba + entornos
# ------------------------------------------------
RUN set -euxo pipefail && \
    wget -O /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash /tmp/miniconda.sh -b -p /home/usuario/miniconda3 && \
    rm -f /tmp/miniconda.sh && \
    /home/usuario/miniconda3/bin/conda init bash

# Acepta explícitamente los Términos de Servicio de Anaconda.
RUN /home/usuario/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    /home/usuario/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

ENV PATH=/home/usuario/miniconda3/bin:${PATH} \
    CONDA_EXE=/home/usuario/miniconda3/bin/conda
RUN conda install -y -n base -c conda-forge mamba && conda clean -afy

# FastSurfer env (CPU)
RUN mamba create -y -n fastsurfer python=3.10 && conda clean -afy
RUN conda run -n fastsurfer python -m pip install --upgrade pip && \
    conda run -n fastsurfer python -m pip install --no-cache-dir -r /home/usuario/FastSurfer/requirements.cpu.txt

# Morfometría env
COPY morfometria_env.yml /home/usuario/morfometria_env.yml
RUN (mamba env create -f /home/usuario/morfometria_env.yml || conda env create -f /home/usuario/morfometria_env.yml) && \
    conda clean -afy && \
    rm -f /home/usuario/morfometria_env.yml

# Instalar dependencias del sistema necesarias para Chromium/Chrome en contenedores
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates fonts-liberation wget unzip gnupg2 \
    libnss3 libasound2 libxss1 libxtst6 libxrandr2 libxdamage1 \
    libgtk-3-0 libglib2.0-0 libgbm1 libx11-xcb1 libxshmfence1 \
    libegl1 libgles2 libopengl0 xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# Descargar y descomprimir Google Chrome versión 134
RUN wget -O /tmp/chrome.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/134.0.6998.35/linux64/chrome-linux64.zip && \
    unzip /tmp/chrome.zip -d /opt && mv /opt/chrome-linux64 /opt/chrome134 && \
    ln -sf /opt/chrome134/chrome /usr/bin/google-chrome && chmod +x /opt/chrome134/chrome && \
    rm -f /tmp/chrome.zip

# Descargar y descomprimir Chromedriver para Chrome 134
RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.35/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver.zip -d /opt && \
    mv /opt/chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    rm -rf /opt/chromedriver-linux64 /tmp/chromedriver.zip && \
    chmod +x /usr/bin/chromedriver

# Configuración de las variables de entorno para Chrome
ENV CHROME_BIN=/opt/chrome134/chrome
ENV LD_LIBRARY_PATH=/opt/chrome134:/opt/chrome134/swiftshader:${LD_LIBRARY_PATH}
# Establecer la variable para forzar SwiftShader si se necesitan aceleración por software (WebGL)
ENV LIBGL_ALWAYS_SOFTWARE=1


COPY preprocessing /home/usuario/Bibliografia/pipeline_v2/preprocessing
COPY processing    /home/usuario/Bibliografia/pipeline_v2/processing
COPY recursos      /home/usuario/Bibliografia/pipeline_v2/recursos
COPY main_local.py /home/usuario/Bibliografia/pipeline_v2/main_local.py
COPY extract_patient_name.py /home/usuario/Bibliografia/pipeline_v2/extract_patient_name.py
COPY extract_patient_age.py /home/usuario/Bibliografia/pipeline_v2/extract_patient_age.py
COPY send_email.py /home/usuario/Bibliografia/pipeline_v2/send_email.py
RUN install -m 0644 -D /dev/null /home/usuario/Bibliografia/pipeline_v2/__init__.py
# ------------------------------------------------
# Xvfb + entorno gráfico headless
# ------------------------------------------------
ENV FASTSURFER_HOME=/home/usuario/FastSurfer \
    SUBJECTS_DIR=/data/subjects \
    DISPLAY=:99 \
    QT_QPA_PLATFORM=xcb \
    QT_X11_NO_MITSHM=1 \
    GTK_IM_MODULE=none \
    XDG_RUNTIME_DIR=/tmp/runtime \
    PATH=/home/usuario/miniconda3/bin:/home/usuario/fsl/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
RUN mkdir -p /tmp/runtime && chmod 1777 /tmp/runtime

RUN cat <<'EOF' > /usr/local/bin/start_xvfb.sh
#!/usr/bin/env bash
set -euo pipefail
if ! pgrep -x Xvfb >/dev/null; then
  Xvfb :99 -screen 0 1720x900x24 &
  disown
  sleep 2
fi
EOF
RUN chmod +x /usr/local/bin/start_xvfb.sh

WORKDIR /home/usuario/Bibliografia/pipeline_v2

# Shell de login para cargar /etc/profile.d/{freesurfer,fsl}.sh
CMD ["bash","-l"]
