from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import videointelligence
from config import openai_api_key, youtube_api_key, google_api_key, google_project_id, bucket_name
import urllib.parse
import openai


def ask_openai(api_key: str, question: str):
    """ expands generic question into a collection of searchable queries """
    openai.api_key = api_key
    prompt = (f"Expand the following topics into a list of search queries: {question}\n"
              f"Answer:")

    response = openai.Completion.create(
        engine="davinci",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5,
    )

    answer = response.choices[0].text.strip()
    return answer


def google_video_search(google_api_key, search_term, num_results=5):
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


def phraise_to_topics(phraise:str, num_results:int=5):
    """ collect videos matching not only a general question, but videos for related and necessary steps as well """
    topics = ask_openai(open_api_key, phraise)
    videos = []
    for topic in topics:
         videos = list(itertools.chain(videos, google_video_search(google_api_key, search_term, num_results=5)))
                       

def autolabel_frames(gspath:str)->list:
    """ autodetect recognizable objects in the video with GoogleVideoIntelligence """                   
    # gspath - gs://bucket/path2file/filename in the gcs bucket
                       
    video_client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.Feature.LABEL_DETECTION]

    with io.open(gspath, "rb") as movie:
        input_content = movie.read()

    operation = video_client.annotate_video(
        request={"features": features, "input_content": input_content}
    )
    
    result = operation.result(timeout=90)
    
    # Process frame level label annotations for all frames
    frame_labels = result.annotation_results[0].frame_label_annotations
    frames = []
                       
    for frame_label in frame_labels:
        
        categories = frame_label.get('category_entities')
        labels = []
                       
        for frame in frame_label.frames:
            time_offset = frame.time_offset.seconds + frame.time_offset.microseconds / 1e6
            confidence = frame.get('confidence')

            # Print available key-value pairs for the frame
            frameid = frame.entity.get('entity_id')
            description = frame.entity.get('description')
            language = frame.entity.get('language_code')
            
            attributes = []
            if frame.attributes:
                for attribute in frame.attributes:
                    attributes.append({'name': attribute.name, 'value': attribute.value, 'confidence': attribute.confidence })
                       
            label = {'id': frameid, 
                     'description': description, 
                     'confidence': confidence, 
                     'time_offset': time_offset, 
                     'language': language, 
                     'attributes': attributes }
            labels.append(label)
            
        frame = { 'categories': categories, 'labels': labels }
        frames.append(frame)
    
    return frames