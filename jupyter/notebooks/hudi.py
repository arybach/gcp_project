from pyspark.sql import SparkSession
from pyspark.sql.functions import input_file_name, gzip
from pyspark.sql.types import StructType, StructField, StringType, BinaryType


def jpeg_bundle_to_hudi(path2jpegs:str, path2hudi_file:str)->str:
    """ fetches all frames with .jpeg extensions from a path2jpegs and saves them as a parquet file in hudi """
    try:
        # Create a SparkSession
        spark = SparkSession.builder.appName("Create DataFrame from JPEG files").getOrCreate()

        # Define the schema for the DataFrame
        schema = "filename STRING"

        # Create a DataFrame from the JPEG files
        df = spark.read.format("image").load("/path/to/jpegs/*")

        # Add a new column with the filename
        df = df.withColumn("filename", input_file_name())

        # Select only the filename column
        df = df.select("filename")

        # Write the DataFrame as a Parquet file
        df.write.parquet(f"{path2hudi_file}")
    except Exception as e:
        return e
        
    return path2hudi_file


def video_bundle_to_hudi(path2video:str, path2hudi_file:str)->str:

    # Create a SparkSession
    spark = SparkSession.builder.appName("Write data to Hudi").getOrCreate()

    # Define the schema for the DataFrame
    schema = StructType([
        StructField("filename", StringType()),
        StructField("video", BinaryType()),
        StructField("audio", BinaryType()),
        StructField("captions", StringType())
    ])

    # Create a DataFrame from the files
    df = spark.read.format("binaryFile") \
        .option("pathGlobFilter", "*.mp4") \
        .load("/path/to/videos/*")

    # Add a new column with the filename
    df = df.withColumn("filename", input_file_name())

    # Compress the video data with gzip
    df = df.withColumn("video", gzip(df["content"]))

    # Load the audio and captions data
    df = df.join(spark.read.format("binaryFile")
        .option("pathGlobFilter", "*.mp3")
        .load("/path/to/audios/*"), "filename") \
        .join(spark.read.format("json")
        .option("pathGlobFilter", "*.json")
        .load("/path/to/captions/*"), "filename")

    # Write the DataFrame as a Hudi table
    hudi_options = {
        "hoodie.insert.shuffle.parallelism": "2",
        "hoodie.upsert.shuffle.parallelism": "2",
        "hoodie.datasource.write.recordkey.field": "filename",
        "hoodie.datasource.write.partitionpath.field": "filename",
        "hoodie.datasource.write.table.name": "my_hudi_table",
        "hoodie.datasource.write.operation": "upsert",
        "hoodie.table.type": "COPY_ON_WRITE"
    }

    df.write \
      .format("org.apache.hudi") \
      .options(**hudi_options) \
      .mode("append") \
      .save("/path/to/my_hudi_table")
