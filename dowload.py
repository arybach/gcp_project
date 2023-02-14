# sudo apt install yt-dlp # 2023.1.6 version
# wget https://github.com/yt-dlp/yt-dlp/releases/download/2023.01.06/yt-dlp.tar.gz
# tar -xvzf yt-dlp.tar.gz
# cd yt-dlp
# sudo python3 setup.py install
# yt-dlp --version

import os, re
#import yt_dlp 
import json
import subprocess
from pydub import AudioSegment  # to extract as podcast
from youtube_dl import YoutubeDL
from credentials.config import google_api_key
from nltk import word_tokenize
from nltk.util import ngrams
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def to_milliseconds(timestamp):
    hours, minutes, seconds = map(int, timestamp.split('.')[0].split(':'))
    milliseconds = int(timestamp.split(' ')[0].split('.')[-1])
    return (hours * 60 * 60 + minutes * 60 + seconds) * 1000 + milliseconds

def from_milliseconds(milliseconds):
    hours = milliseconds // (60 * 60 * 1000)
    milliseconds = milliseconds % (60 * 60 * 1000)
    minutes = milliseconds // (60 * 1000)
    milliseconds = milliseconds % (60 * 1000)
    seconds = milliseconds // 1000
    milliseconds = milliseconds % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
def cosine_similarity(text1, text2):
    tfidf = TfidfVectorizer().fit_transform([text1, text2])
    return cosine_similarity(tfidf)[0][1]

def aggregate_texts(start_time, end_time, text, next_start_time, next_end_time, next_text):
    similarity = cosine_similarity(text, next_text)
    if similarity > 0.5:
        aggregated_text = text + " " + next_text
        aggregated_start_time = start_time
        aggregated_end_time = next_end_time
        return aggregated_start_time, aggregated_end_time, aggregated_text, True
    else:
        return start_time, end_time, text, False

# Define the timecodes
# Define the timecodes
timecodes = [
    {"name": "00:00 Agenda", "time": "00:00"},
    {"name": "00:28 OLAP vs OLTP", "time": "00:28"},
    {"name": "02:18 What is a data warehouse", "time": "02:18"},
    {"name": "03:36 BigQuery", "time": "03:36"},
    {"name": "05:19 BigQuery interface", "time": "05:19"},
    {"name": "07:04 Querying public datasets", "time": "07:04"},
    {"name": "07:42 BigQuery costs", "time": "07:42"},
    {"name": "09:02 Create an external table", "time": "09:02"},
    {"name": "12:04 Partitioning", "time": "12:04"},
    {"name": "18:45 Clustering", "time": "18:45"}
]

# Define a function to extract the text between two timecodes
def extract_text(file, start_time, end_time):
    # Open the .vtt file
    with open(file, "r") as f:
        lines = f.readlines()
        
    # Remove the first three lines (WEBVTT, Kind: captions, Language: en)
    lines = lines[3:]
    
    # Concatenate the lines into one string
    content = "".join(lines)
    
    # Use regular expressions to extract the text between the start and end timecodes
    pattern = f"{start_time}.*?{end_time}"
    text = re.search(pattern, content, re.DOTALL).group()
    
    # Clean up the text by removing the timecodes and newline characters
    text = re.sub(f"{start_time}.*?\n", "", text)
    text = re.sub(f"{end_time}.*?\n", "", text)
    text = re.sub("\n", "", text)
    
    return text

def aggregate_text_by_timecodes(file_vtt:str, timecodes:list) -> dict:
    # Aggregate the text for each timecode
    aggregated_text = {}
    for i in range(len(timecodes) - 1):
        start_time = timecodes[i]["time"]
        end_time = timecodes[i + 1]["time"]
        
        # Extract the text between the start and end timecodes
        text = extract_text(file_vtt, start_time, end_time)
        
        # Add the text to the aggregated text dictionary
        aggregated_text[timecodes[i]["name"]] = {
            "start": start_time,
            "end": end_time,
            "aggregated_text": text
        }
        
    # Print the aggregated text
    for name, data in aggregated_text.items():
        print(f"{name}: {data}")
        
    return aggregated_text

# just save in json w/o aggregation
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
                    "caption": caption
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


def fetch_video_and_subtitles(link:str, lbl:str) -> str:
    """ fetches video in 720p .mp4 format from Youtube url and captions in .vtt format -> return filename """
    #link = "https://www.youtube.com/watch?v=L04lvYqNlc0"
    path2file = "videos/" + lbl

    yt = YoutubeDL().extract_info(url=link, download=False)
    title = yt.get("title")
    description = yt.get('description')
    print(title)
    print(description)

    cmddl = [
         "yt-dlp", "-N", "16", "--format", 
         "bv[height=720][ext=mp4]+ba[ext=m4a]",
         "-o", f"{path2file}/%(title)s.%(ext)s",
         link
    ]
    result = subprocess.run(cmddl, stdout=subprocess.PIPE)
    print("Downloaded: ", result.stdout.decode("utf-8").strip())
    cmdcaps = [
        "yt-dlp", "--write-subs", "--write-auto-subs", "--sub-format", "ass/srt/best", "--sub-langs", "en",
        "-o", f"{path2file}/%(title)s", link 
    ]
    result = subprocess.run(cmdcaps, stdout=subprocess.PIPE)
    print("Downloaded: ", result.stdout.decode("utf-8").strip())
    # os.remove(f"{path2file}/%(title)s.webm")
    #jsonfile = agg_vtt_save_as_json(f'{path2file}/{title}.en.vtt' )
    jsonfile = vtt_to_json(f'{path2file}/{title}.en.vtt' )
    print(jsonfile)


if __name__ == "__main__":
    # week_1
    lbl = 'lectures'
    links = [   "https://youtu.be/jrHljAoD6nM" ]

    # links = [   "https://www.youtube.com/watch?v=EYNwNlOrpr0&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=2JM-ziJt0WI&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=hCAIVe9N0ow&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=B1WwATwf-vY&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=hKI6PkPhpa0&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=QEcps_iskgg&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=18jIzE41fJ4&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=Hajwnmj0xfQ&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=dNkEgO-CExg&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb",
    #             "https://www.youtube.com/watch?v=ae-CV2KfoN0&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb"        
    #         ]
           
    # # without playlist
    # week_3 = [ "https://youtu.be/jrHljAoD6nM", 
    #            "https://youtu.be/jrHljAoD6nM?t=726",
    #            "https://youtu.be/-CqXf7vhhDs",
    #            "https://youtu.be/k81mLJVX08w",
    #            "https://youtu.be/eduHi1inM4s",
    #            "https://youtu.be/B-WtpB0PuG4",
    #            "https://youtu.be/BjARzEWaznU",
    #             ]
    # BQ resources:
    # https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/week_3_data_warehouse/big_query_ml.sql
    # https://cloud.google.com/bigquery-ml/docs/tutorials
    # https://cloud.google.com/bigquery-ml/docs/analytics-reference-patterns
    # https://cloud.google.com/bigquery-ml/docs/reference/standard-sql/bigqueryml-syntax-create-glm
    # https://cloud.google.com/bigquery-ml/docs/reference/standard-sql/bigqueryml-syntax-preprocess-overview
    # Deploying
    # https://github.com/DataTalksClub/data-engineering-zoomcamp/blob/main/week_3_data_warehouse/extract_model.md
    
    for link in links:
        fetch_video_and_subtitles(link, lbl)
    
    # jsonfiles = []
    # vttlist = os.listdir("/media/groot/_data/Books/Gcpzoomcamp/videos/" + lbl)
    # print(vttlist)
    # for vttf in vttlist:
    #     if re.findall('.vtt', vttf):
    #         #jsonfiles.append(vtt_to_json("/media/groot/_data/Books/Gcpzoomcamp/videos/" + lbl + '/' + vttf)) 
    #         jsonfiles.append(agg_vtt_save_as_json("/media/groot/_data/Books/Gcpzoomcamp/videos/" + lbl + '/' + vttf)) 

    #print(jsonfiles)    