# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
ARG OWNER=jupyter
ARG BASE_CONTAINER=$OWNER/scipy-notebook
FROM $BASE_CONTAINER

LABEL maintainer="Alex R <mats.tumblebuns@gmail.com>"

# Fix DL4006
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

USER root

# Spark dependencies
# Default values can be overridden at build time
# (ARGS are in lower case to distinguish them from ENV)
ARG spark_version="3.3.2"
ARG hadoop_version="3"
ARG spark_checksum="4cd2396069fbe0f8efde2af4fd301bf46f8c6317e9dea1dd42a405de6a38380635d49b17972cb92c619431acece2c3af4c23bfdf193cedb3ea913ed69ded23a1"
ARG openjdk_version="11"

ENV APACHE_SPARK_VERSION="${spark_version}" \
    HADOOP_VERSION="${hadoop_version}"
ENV JUPYTER_ENABLE_LAB=yes
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends \
    "openjdk-${openjdk_version}-jre-headless" \
    ca-certificates-java && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Spark installation
WORKDIR /tmp
RUN wget -q "https://archive.apache.org/dist/spark/spark-${APACHE_SPARK_VERSION}/spark-${APACHE_SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" && \
    echo "${spark_checksum} *spark-${APACHE_SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" | sha512sum -c - && \
    tar xzf "spark-${APACHE_SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" -C /usr/local --owner root --group root --no-same-owner && \
    rm "spark-${APACHE_SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz"

# Add Google Cloud Storage connector
# ARG gcs_connector_version="hadoop3-2.2.0"
# ENV GCS_CONNECTOR_VERSION="${gcs_connector_version}"

# RUN wget -q "https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-${GCS_CONNECTOR_VERSION}.jar" -P "${SPARK_HOME}/jars/"
# from pyspark.conf import SparkConf
# from pyspark.context import SparkContext
# credentials_location = "path/to/google_credentials.json"
# conf = SparkConf() \
# 	.setMaster('local[*]') \
# 	.setAppName('test') \
# 	.set("spark.jars", "/path2/apache-spark/3.3.2/jars/gcs-connector-hadoop3-latest.jar" ) \
# 	.set("spark.hadoop.google.cloud.auth.servicee.account.enable", "true") \
# 	.set("spark.hadoop.google.cloud.auth.service.account.json.keyfile", credentials_location)
	
# sc = SparkContext(conf=conf)

# hadoop_conf = sc._jsc.hadoopConfiguration()

# hadoop_conf.set("fs.AbstractFileSystem.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS")
# hadoop_conf.set("fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS")
# hadoop_conf.set("fs.gs.auth.service.account.json.keyfile", credentials_location)
# hadoop_conf.set("fs.gs.auth.service.account.enable", "true")
	


WORKDIR /usr/local

# Configure Spark
ENV SPARK_HOME=/usr/local/spark
ENV SPARK_OPTS="--driver-java-options=-Xms1024M --driver-java-options=-Xmx4096M --driver-java-options=-Dlog4j.logLevel=info" \
    PATH="${PATH}:${SPARK_HOME}/bin"

RUN ln -s "spark-${APACHE_SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}" spark && \
    # Add a link in the before_notebook hook in order to source automatically PYTHONPATH
    mkdir -p /usr/local/bin/before-notebook.d && \
    ln -s "${SPARK_HOME}/sbin/spark-config.sh" /usr/local/bin/before-notebook.d/spark-config.sh

# Fix Spark installation for Java 11 and Apache Arrow library
# see: https://github.com/apache/spark/pull/27356, https://spark.apache.org/docs/latest/#downloading
RUN cp -p "${SPARK_HOME}/conf/spark-defaults.conf.template" "${SPARK_HOME}/conf/spark-defaults.conf" && \
    echo 'spark.driver.extraJavaOptions -Dio.netty.tryReflectionSetAccessible=true' >> "${SPARK_HOME}/conf/spark-defaults.conf" && \
    echo 'spark.executor.extraJavaOptions -Dio.netty.tryReflectionSetAccessible=true' >> "${SPARK_HOME}/conf/spark-defaults.conf"

# latest version of ffmpeg is not in the oficial repos
RUN apt-get update && apt-get install -y wget

# Download and extract FFmpeg
RUN apt-get update && apt-get install -y wget
RUN wget https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2
RUN tar xjf ffmpeg-snapshot.tar.bz2
RUN cd ffmpeg && ./configure --enable-shared
RUN cd ffmpeg && make -j$(nproc) && make install

# ffmpeg dependencies and latest versions:
# libavutil      58.  2.100
# libavcodec     60.  3.100
# libavformat    60.  3.100
# libavdevice    60.  1.100
# libavfilter     9.  3.100
# libswscale      7.  1.100
# libswresample   4. 10.100
# libpostproc    57.  1.100
# sudo apt-get install -y libgomp1 libavcodec-extra libavformat-dev libavutil-dev libswscale-dev && \
# installing yje exact versions as repos have not yet been updated  

# Update the package lists and install necessary packages 
RUN sudo apt-get update && \
    sudo apt-get install -y libavutil58=58.2.100 libavcodec60=60.3.100 libavformat60=60.3.100 libavdevice60=60.1.100 libavfilter9=9.3.100 libswscale7=7.1.100 libswresample4=4.10.100 libpostproc57=57.1.100 && \
    sudo apt-get install -y openssl && \
    sudo apt-get install -y python3.9 python3-pip gfortran && \
    sudo apt-get install -y gcc g++ python3-dev git ninja-build && \
    sudo apt-get install -y wget bzip2 ca-certificates libglib2.0-0 libxext6 libsm6 libxrender1 && \
    sudo apt-get install -y libprotobuf-dev protobuf-compiler python3-protobuf python3-grpcio && \
    sudo rm -rf /var/lib/apt/lists/*

# partitioning doesn't work without proepr permissions
# USER ${NB_UID}

# Install python modules (list is shorter than in requirments.txt file)
RUN mamba update mamba && \
    mamba config --add channels conda-forge && \
    mamba config --add channels bioconda && \
    mamba install --quiet --yes \
    'pyarrow' 'opencv' 'pandas' 'yt-dlp' 'pipenv' 'pyOpenSSL' 'ffmpeg' 'scikit-learn<=1.2.1' 'pydub<=0.25.1' 'moviepy' 'skimage' && \
    mamba install --quiet --yes \
    'youtube-dl' 'nltk<=3.8.1' 'pandas<=1.5.3' 'pandasql<=0.7.3' 'google-cloud-storage' 'google-api-python-client' 'openai' 'google-cloud-videointelligence' && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home" && \
    fix-permissions "/home/${NB_USER}"

WORKDIR /home/work
