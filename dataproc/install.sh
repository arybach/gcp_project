#!/bin/bash

# install on all nodes (is this for UDF functions to work? as spark nodes run on java, only pyspark is a Python wrapper)
apt-get update && \
apt-get install -y libgomp1 libavcodec-extra libavformat-dev libavutil-dev libswscale-dev && \
apt-get install -y openssl && \
apt-get install -y python3.9 python3-pip ffmpeg gfortran && \
apt-get install -y gcc g++ python3-dev git ninja-build && \
apt-get install -y wget bzip2 ca-certificates libglib2.0-0 libxext6 libsm6 libxrender1 && \
apt-get install -y libprotobuf-dev protobuf-compiler python3-protobuf python3-grpcio && \
rm -rf /var/lib/apt/lists/*

# Install python modules (anaconda should be installed already) - these will be run in jupyter even if they don't work on spark nodes
conda update conda && \
conda config --add channels conda-forge && \
conda config --add channels bioconda && \
conda install --quiet --yes \
'pyarrow' 'opencv' 'pandas' 'yt-dlp' 'pipenv' 'pyOpenSSL' 'ffmpeg' 'scikit-learn<=1.2.1' 'pydub<=0.25.1' && \
conda install --quiet --yes \
'youtube-dl' 'nltk<=3.8.1' 'pandas<=1.5.3' 'pandasql<=0.7.3' && \
conda clean --all -f -y
# conda clean --all -f -y && \
# fix-permissions "${CONDA_DIR}" && \
# fix-permissions "/home/groot"

# jupyter home
# WORKDIR /home/groot/notebooks
