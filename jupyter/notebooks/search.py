from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import storage
from config import openai_api_key, youtube_api_key, google_api_key, google_project_id, bucket_name
import urllib.parse
import openai
import io
import fnmatch
from google.cloud import videointelligence_v1p3beta1 as videointelligence

def ask_openai(api_key: str, question: str):
    """ expands generic question into a collection of searchable queries """
    openai.api_key = api_key
    prompt = (f"{question}\n"
              f"Answer:")

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5,
    )

    answer = response.choices[0].text.strip()
    return answer


def google_video_search(api_key, search_term, num_results=5):
    """ finds best matching videos with default search settings """
    youtube = build("youtube", "v3", developerKey=api_key)
    query = urllib.parse.urlencode({'q': search_term})
    search_response = youtube.search().list(
        q=query,
        type='video',
        part='id,snippet',
        maxResults=num_results
    ).execute()

    videos = []
    for search_result in search_response.get("items", []):
        videos.append(search_result)

    return videos


def autolabel_frames(bucket_name:str, gspath:str)->list:
    """ autodetect recognizable objects in the video with GoogleVideoIntelligence """                   
    # bucket_name = sparkhudi
    # gspath - gs://bucket/path2file/filename in the gcs bucket
                       
    # Create a GCS client
    client = storage.Client()
    confidence_threshold = 0.5
    
    # Get a reference to the GCS bucket and blob
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gspath)

    # Download the video file as bytes
    input_content = blob.download_as_bytes()

    # Annotate the video using the Video Intelligence API
    video_client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.Feature.LABEL_DETECTION]
   
    label_detection_config = videointelligence.LabelDetectionConfig(
        label_detection_mode=videointelligence.LabelDetectionMode.SHOT_AND_FRAME_MODE,
        frame_confidence_threshold=confidence_threshold)

    request = videointelligence.AnnotateVideoRequest(
        input_content=input_content,
        features=features,
        video_context=videointelligence.VideoContext(
            label_detection_config=label_detection_config))

    operation = video_client.annotate_video(request=request)

    result = operation.result(timeout=900)
    
    # Process frame level label annotations for all frames
    frame_labels = result.annotation_results[0].frame_label_annotations
    print("Frame labels:")
    print(frame_labels)
    print("All annotation results:")
    print(result.annotation_results)
    frames = []
                       
    for frame_label in frame_labels:
        
        if frame_label.category_entities:
            categories = frame_label.category_entities
        
        labels = []
                       
        for frame in frame_label.frames:
            components = dir(frame)
            if 'time_offset' in components:
                time_offset = frame.time_offset.seconds + frame.time_offset.microseconds / 1e6
            
            if 'confidence' in components:
                confidence = frame.confidence

            # Print available key-value pairs for the frame
            # frameid = frame.entity.entity_id
            if 'description' in components:
                description = frame.entity.description
            
            if 'language_code' in components:
                language = frame.entity.language_code
            
            if 'attributes' in components:

                attributes = []
                for attribute in frame.attributes:
                    attributes.append({'name': attribute.name, 'value': attribute.value, 'confidence': attribute.confidence })
                # if there are no attributes - doesn't make sense to keep the frame and labels
                label = { 'id': frameid, 
                         'description': description, 
                         'confidence': confidence, 
                         'time_offset': time_offset, 
                         'language': language, 
                         'attributes': attributes }
                labels.append(label)
        
        if labels:
            frame = { 'categories': categories, 'labels': labels }
            frames.append(frame)
    
    return frames


def get_stream_highlights_dataset()->list:
    """ returns list of dicts with video urls from most popular gaming streamers """
    answer = ask_openai(openai_api_key, 'who are the most popular youtube gaming streamers? please provide a list of names')
    
    streamers = answer.split('\n')
    streams = []
    for streamer in streamers:
        streamer = re.sub(r'\d+.\s', '', streamer)
        search_term = f"Highlights of the most popular streams of {streamer} - up to half an hour long"
        print(search_term)
        results = google_video_search(youtube_api_key, search_term, num_results=5)
        for res in results:
            if res['id']['kind'] == 'youtube#video':
                video_id = res['id']['videoId']
                description = res['snippet']['description']
                url = f"https://www.youtube.com/watch?v={video_id}"
                title = res['snippet']['title']
                filename = f"{title}.mp4"
                channel_title = res['snippet']['channelTitle']
                channel_id = res['snippet']['channelId']

            streams.append({"channel": streamer, "channel_title": channel_title,'description': description, "video_id": video_id, 'url': url, 'title': title, 'filename': filename})
 
    return streams


def get_fpv_drone_footage_dataset()->list:
    """ returns list of dicts with video urls from most popular fpv videos """
    answer = ask_openai(openai_api_key, 'what are the most popular youtube channels for fpv drone footage? please provide a list of names')
    
    channels = answer.split('\n')
    streams = []
    for channel in channels:
        channel = re.sub(r'\d+.\s', '', channel)
        search_term = f"Highlights of the most popular fpv videos in the {channel} channel - up to half an hour long"
        print(search_term)
        results = google_video_search(youtube_api_key, search_term, num_results=5)
        for res in results:
            if res['id']['kind'] == 'youtube#video':
                video_id = res['id']['videoId']
                description = res['snippet']['description']
                url = f"https://www.youtube.com/watch?v={video_id}"
                title = res['snippet']['title']
                filename = f"{title}.mp4"
                channel_title = res['snippet']['channelTitle']
                channel_id = res['snippet']['channelId']

            streams.append({"channel": channel_id, "channel_title": channel_title,'description': description, "video_id": video_id, 'url': url, 'title': title, 'filename': filename})

    return streams

#'https://www.youtube.com/watch?v=7N7hG21TPUA'


def get_youtube_channel_dataset(channel_id:str = "3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb")->list:
    """ fetches all urls with description, title and so on given a channel id"""
    MAX_RESULTS = 100
    
    # Make the API request to fetch videos from the channel
    url = f"https://www.googleapis.com/youtube/v3/search?key={youtube_api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults={MAX_RESULTS}"
    response = requests.get(url)
    json_data = response.json()

    # Process the API response and extract video URLs, titles, descriptions, and filenames
    videos = []
    for item in json_data["items"]:
        if item["id"]["kind"] == "youtube#video":
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            description = item["snippet"]["description"]
            filename = f"{title}.mp4"
            url = f"https://www.youtube.com/watch?v={video_id}"
            channel_id = item['snippet']['channelId']
            channel_title = item['snippet']['channelTitle']
            
            videos.append({"channel": channel_id, "channel_title": channel_title,'description': description, "video_id": video_id, 'url': url, 'title': title, 'filename': filename})

    return videos