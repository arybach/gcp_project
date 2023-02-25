# built with ubuntu 20.04
FROM apache/zeppelin:0.10.1 

# Add metadata
LABEL maintainer="Alex R - mats.tumblebuns@gmail.com"
LABEL description="Enhanced appache/zeppelin:0.10.1 image with ffmpeg, yt-dlp and opencv installation"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

USER root

# Create the zeppelin user and give them sudo privileges
RUN groupadd -g 1001 zeppelin && \
    useradd -u 1001 -g 1001 -s /bin/bash -m zeppelin && \
    echo "zeppelin ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    chown -R zeppelin:zeppelin /opt

ENV UID=1001
ENV GID=1001

WORKDIR /opt

# Update the system and install ffmpeg and yt_dlp and deps (libgomp1 is pandas dependency) - conda only supports python 3.9
RUN apt-get update && \
    apt-get install -y libgomp1 libavcodec-extra libavformat-dev libavutil-dev libswscale-dev && \
    apt-get install -y openssl && \
    apt-get install -y python3.9 python3-pip ffmpeg gfortran && \
    apt-get install -y gcc g++ python3-dev git ninja-build && \
    apt-get install -y wget bzip2 ca-certificates libglib2.0-0 libxext6 libsm6 libxrender1 && \
    apt-get install -y libprotobuf-dev protobuf-compiler python3-protobuf python3-grpcio && \
    rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN rm -rf /opt/conda && \
    wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -afy && \
    rm -rf /opt/conda/pkgs/* && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> /opt/zeppelin/conf/zeppelin-env.sh && \
    echo "conda activate pyspark_env" >> /opt/zeppelin/conf/zeppelin-env.sh && \
    chown -R zeppelin /opt/conda

ENV PATH="/opt/conda/bin:${PATH}"

# Copy the requirements file into the Docker image
COPY requirements.txt .

# Install dependencies to pyspark_env environment
RUN conda config --add channels conda-forge && \
    conda config --add channels anaconda && \
    conda install -y opencv grpcio protobuf pyarrow pandas conda-pack yt-dlp pipenv pyOpenSSL ffmpeg && \
    conda clean -afy && \
    rm -rf /opt/conda/pkgs/*

COPY --chown=zeppelin:zeppelin pyspark_env.tar.gz /opt/pyspark_env.tar.gz

# extract the pyspark environment from mounted ./opt:/opt
RUN mkdir -p /opt/zeppelin/pyspark_env && \
    tar xzf /opt/pyspark_env.tar.gz -C /opt/zeppelin/pyspark_env && \
    . /opt/conda/etc/profile.d/conda.sh && \
    conda activate /opt/zeppelin/pyspark_env && \
    conda-unpack