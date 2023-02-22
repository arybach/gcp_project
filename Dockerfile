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

# Update the system and install ffmpeg and yt_dlp and deps (libgomp1 is pandas dependency)
RUN apt-get update && \
    apt-get install -y libgomp1 libavcodec-extra libavformat-dev libavutil-dev libswscale-dev && \
    apt-get install -y openssl && \
    apt-get install -y python3.10 python3-pip ffmpeg gfortran && \
    apt-get install -y gcc g++ python3-dev git ninja-build && \
    apt-get install -y wget bzip2 ca-certificates libglib2.0-0 libxext6 libsm6 libxrender1 && \
    rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN rm -rf /opt/conda && \
    wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -afy && \
    rm -rf /opt/conda/pkgs/* && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc && \
    chown -R zeppelin /opt/conda

ENV PATH="/opt/conda/bin:${PATH}"

# Copy the requirements file into the Docker image
COPY requirements.txt .

# Install all dependencies and create+activate a new conda environment with Python 3.10
RUN conda install -y opencv && \
    pip3 install --no-cache-dir --upgrade pip setuptools yt-dlp pipenv pyOpenSSL && \
    pip3 install --no-cache-dir -r requirements.txt && \
    /opt/conda/bin/conda create --name py310 python=3.10 -y && \
    echo "conda activate py310" >> /opt/zeppelin/conf/zeppelin-env.sh

# Set the interpreter properties in zeppelin-site.xml
RUN echo "<property><name>zeppelin.python</name><value>/opt/conda/envs/py310/bin/python</value></property>" >> /opt/zeppelin/conf/zeppelin-site.xml \
    && echo "<property><name>zeppelin.pyspark.python</name><value>/opt/conda/envs/py310/bin/python</value></property>" >> /opt/zeppelin/conf/zeppelin-site.xml

RUN rm -rf /root/.cache  && \
    chown -R zeppelin /opt/zeppelin/notebook/ 

# Set environment variables
# ENV DEBUG_LOG_LEVEL=debug
# ENV DEBUG_LOG_FILE=/opt/zeppelin/logs/debug.log

# Set the entrypoint to Zeppelin
# ENTRYPOINT ["/bin/bash", "-c", "python3 -m pdb /opt/zeppelin/bin/zeppelin.sh --debug --log-level=$DEBUG_LOG_LEVEL --log-file=$DEBUG_LOG_FILE"]
ENTRYPOINT ["/opt/zeppelin/bin/zeppelin.sh"]

# docker build -t zeppelin_ffmpeg_ytdlp_cv2:0.10.1 /home/groot/gcp_project/
