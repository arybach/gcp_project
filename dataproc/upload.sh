#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: ./upload.sh bucket-name"
    exit
fi

PROJECT=$(gcloud config get-value project)
BUCKET=$1
INSTALL=gs://$BUCKET/install.sh


#upload install
gsutil cp install.sh $INSTALL
# -m (multithreaded) -r (reqursive)
# PREFIX='data'
# gsutil -m cp -r home/data gs://$BUCKET/$PREFIX

# BUCKET is sparkhudi
gcloud dataproc clusters create sparkhudi \
    --enable-component-gateway \
    --bucket $BUCKET \
    --region $REGION \
    --subnet public \
    --zone $ZONE \
    --single-node \
    --master-machine-type n1-standard-8 \
    --master-boot-disk-type pd-ssd \
    --master-boot-disk-size 80 \
    --image-version 2.1-ubuntu20 \
    --project gcpzoomcamp \
    -–optional-components=HUDI,ANACONDA,JUPYTER \
    -–initialization-actions=$INSTALL