# collection of functions useful in dev stage
from youtube_dl import YoutubeDL
from google.cloud import storage
import re, os, json, subprocess
import yt_dlp
import fnmatch

def bulk_upload(path2file: str, bucket_name: str):
    """ Upload locally stored files to GCS bucket with subdirectories based on file type. """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # Create subdirectories
        blob_mp4 = bucket.blob('mp4/')
        blob_mp4.upload_from_string('')
        blob_vtt = bucket.blob('vtt/')
        blob_vtt.upload_from_string('')
        blob_json = bucket.blob('json/')
        blob_json.upload_from_string('')

        # Upload files
        for filename in os.listdir(path2file):
            if filename.endswith('.mp4'):
                blob = bucket.blob('mp4/' + filename)
                blob.upload_from_filename(path2file + '/' + filename)
            elif filename.endswith('.vtt'):
                blob = bucket.blob('vtt/' + filename)
                blob.upload_from_filename(path2file + '/' + filename)
            elif filename.endswith('.json'):
                blob = bucket.blob('json/' + filename)
                blob.upload_from_filename(path2file + '/' + filename)

        return True

    except Exception as e:
        return e
    
def fetch_files_from_bucket(bucket_name:str, suffix:str) -> list:
    """Fetch files from a GCS bucket and subfolder."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name + "/" + suffix)
        file_list = [blob.name for blob in bucket.list_blobs() ]

        return file_list

    except Exception as e:
        return e
    

def fetch_files_locally(directory:str, extension:str='vtt')->list:
    """ finds all files with specified extension in supplied directory """
    ffiles = []
    for file in os.listdir(directory):
        if fnmatch.fnmatch(file, f'*.{extension}'):
            ffiles.append(file)
    return ffiles


def extract_video_info(url:str)->dict:
    yt = YoutubeDL(params={'verbose': True}).extract_info(url, download=False)
    title = yt.get("title")
    yt = YoutubeDL().extract_info(url=links[0], download=False)
    title = yt.get("title")
    description = yt.get('description')
    return { 'title': title, 'description': description }


def vtt_to_json(vtt_file_path:str)->str:
    """ Call the function to convert a .vtt file to a .json file
    vtt_to_json('path/to/file.vtt')
    """
    # Open the .vtt file and read its contents
    with open(vtt_file_path, 'r') as f:
        vtt_data = f.read()

    # Split the VTT data into lines
    lines = vtt_data.split("\n")

    # Skip the first three lines (WEBVTT, Kind, Language)
    lines = lines[3:]

    # Initialize an empty list to store the captions
    captions = []

    # Loop through the remaining lines
    i = 0
    while i < len(lines):
        # Extract the start and end times
        times = re.findall(r'\d\d:\d\d:\d\d.\d\d\d', lines[i])
        if times:
            if len(times) > 1:
                start_time = times[0]
                end_time = times[1]
            else: # link to a diff video witha timestamp
                start_time = times[0]
                end_time = times[0]

            # Initialize an empty list to store the caption text
            caption_text = []

            # Move to the next line
            i += 1

            # Continue until we reach a line with just times
            while i < len(lines) and re.search(r'\d\d:\d\d:\d\d.\d\d\d', lines[i]) is None:
                caption_text.append(lines[i].strip())
                i += 1

            # Join the lines of caption text
            caption = " ".join(caption_text)

            # Add the start time, end time, and caption text to the captions list
            if caption and caption != " ":
                captions.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "caption": caption.strip()
                })
        else:
            i += 1

    # Convert the captions list to JSON
    captions_json = json.dumps(captions, indent=4)

    # Save the JSON data to a file
    json_file_path = vtt_file_path.replace(".vtt", ".json")
    with open(json_file_path, 'w') as f:
        f.write(captions_json)

    return json_file_path

def upload_to_gcs(path2file: str, fnames: list, bucket_name: str) -> list:
    """Upload the video or subtitle files to the specified GCS bucket"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        object_names = []
        for fname in fnames:
            object_name = fname
            blob = bucket.blob(object_name)
            blob.upload_from_filename(fname)
            object_names.append(object_name)

        return object_names
    except Exception as e:
        return [f"Error uploading {fname}: {e}" for fname in fnames]
    
# cut out a part of the video
#!ffmpeg -i input.mp4 -ss 00:01:30 -to 00:02:30 -c copy output.mp4
def download_video(link: str, path2file: str) -> list:
    """Download the video in mp4 format with 720p resolution and subtitle files in .vtt format to the specified GCS bucket."""
    #try:
        # Download the video and subtitle files to the local machine
    cmdcaps = [
        "yt-dlp", "-N", "16", "--format", "bv[height=720][ext=mp4]+ba[ext=m4a]",
        "--write-subs", "--write-auto-subs", "--sub-format", "ass/srt/best", "--sub-langs", "en",
        "-o", f"{path2file}/%(title)s.%(ext)s", link
    ]
    result = subprocess.run(cmdcaps, capture_output=True, text=True)
    output_lines = result.stdout.strip().split('\n')
    
    for line in output_lines:
        if '[download]' in line and 'Destination' in line:
            filename = line.split('Destination: ')[-1].strip()
        elif '[info]' in line and 'Writing video subtitles to:' in line:
            sub_filename = line.split('Writing video subtitles to: ')[-1].strip()
    
    return filename.replace('.en.vtt','.mp4'), sub_filename.replace('.mp4', '')

