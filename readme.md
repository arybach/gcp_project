This repo attempts the hardly possible customization of Zeppelin.
There's a good reason it is not as widely used as jupyter.
Main reason - very cumbersome process of adding python dependencies and upgrading python version

1. first create pyspark_env.tar.gz using instructions in pyspark_conda.env file (mostly copy and paste)
2. launch zeppelin with docker-compose up -> forward Zeppelin's port (8084 here) via ssh to view in the browser
3. Go to interpreter settings, find spark, click on edit -> uncheck zeppelin.spark.enableSupportedVersionCheck

4. in the zeppelin notebook paste code with conda env python 
%conda pyspark_env

%spark.conf
spark.conf.set("zeppelin.pyspark.python", "/path/to/pyspark_env/bin/python")

# restart kernel, then execute the following

%spark.pyspark

import os
from pyspark.sql import SparkSession

os.environ['PYSPARK_PYTHON'] = '/opt/conda/envs/pyspark_env/bin/python'

spark = SparkSession.builder \
        .master("spark://spark-master:7077") \
        .appName('test') \
        .config("spark.archives", "pyspark_conda_env.tar.gz#environment") \
        .config("spark.pyspark.python", "/opt/conda/envs/pyspark_env/bin/python") \
        .config("spark.pyspark.driver.python", "/opt/conda/envs/pyspark_env/bin/python") \
        .getOrCreate()

if there is no conda kernel available in the image used, it will have to be installed manually.
Hence, i'm replacing zeppelin service with jupyter (zeppelin can still be resurrected using docker-compose_zeppelin.yml)

Jupyter dockerfile installs all the apt-get dependencies + python requirements.txt
Pyspark version should be set to the same one used in the spark-master and spark-worker images
pyspark_env.tar.gz can also be used in this case to propagate python dependencies to master and worker nodes 
similar to above 

Keeping zeppelin setup in case i need it for hudi deployment

##################################################################################
using Jupyter
mkdir jupyter/notebooks
chmod 777 jupyter/notebooks

in the Docker file spark and jdk versions can be chaged
apt-get installs ffmpeg opencv and yt-dlp
python dependencies are installed with mamba

docker-compose up -> ctrl + click on the link to open session with token
