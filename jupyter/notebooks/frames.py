import os
import json
import statistics
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from pydub import AudioSegment
import moviepy.editor as mp

def save_frames_as_images(video_path, frames_dir, start_time=0, end_time=None, every_ms=None):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return "Error: Could not open video file."
    
    if end_time is None:
        end_time = cap.get(cv2.CAP_PROP_POS_MSEC)
    
    if every_ms is None:
        every_ms = 1000 // cap.get(cv2.CAP_PROP_FPS)

    cap.set(cv2.CAP_PROP_POS_MSEC, start_time)
    frame_count = 0
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC)
        if current_time >= end_time:
            break
        
        if current_time % every_ms == 0:
            frame_count += 1
            filename = os.path.join(frames_dir, f"frame{frame_count}.jpg")
            cv2.imwrite(filename, frame)
    
    cap.release()
    
def video_timeline(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return "Error: Could not open video file."
    
    timeline = []
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC)
        timeline.append(current_time)
    
    cap.release()
    
    return np.array(timeline)

def save_frames_as_parquet(video_path, frames_dir, parquet_path):
    filenames = sorted(os.listdir(frames_dir))
    frames = []
    for filename in filenames:
        frame_path = os.path.join(frames_dir, filename)
        frame = cv2.imread(frame_path)
        frames.append(frame)
    
    df = pd.DataFrame({'frame': frames})
    df.to_parquet(parquet_path)

    
def extract_frames(video_path: str, output_path: str, pixel_quantity: int = 6) -> Dict[int, List[List[int]]]:
    """ Extract frames from a video file and save them as RGB pixel arrays in a dictionary """
    # job 1
    begin_time = datetime.now()
    frame_pixels = {}
    with VideoFileClip(video_path) as video:
        for i, frame in enumerate(video.iter_frames()):
            # resize the frame to a fixed width and compute the RGB pixel values
            resized_frame = imresize(frame, (frame.shape[0], pixel_quantity))
            rgb_pixels = resized_frame.reshape(-1, 3).tolist()
            frame_pixels[i] = rgb_pixels
            # save the frame image to disk if needed
            if output_path:
                frame_image = Image.fromarray(frame)
                frame_image.save(f"{output_path}/{i}.jpg")
    print(f"Extracted {len(frame_pixels)} frames from {video_path} in {datetime.now() - begin_time}")
    return frame_pixels


def process_audio(audio_path: str) -> pd.DataFrame:
    """ Process an audio file and return a DataFrame of summary statistics """
    # job 2
    begin_time = datetime.now()
    sound_file = AudioSegment.from_file(audio_path)
    sound_seconds = np.array(sound_file.get_array_of_samples()).reshape(-1, sound_file.channels)
    mean_volume = np.mean(sound_seconds, axis=1)
    median_volume = np.median(sound_seconds, axis=1)
    min_volume = np.min(sound_seconds, axis=1)
    max_volume = np.max(sound_seconds, axis=1)
    sound_df = pd.DataFrame({
        "mean_volume": mean_volume,
        "median_volume": median_volume,
        "min_volume": min_volume,
        "max_volume": max_volume,
    })
    print(f"Processed audio file {audio_path} in {datetime.now() - begin_time}")
    return sound_df


def cut_frames(frame_pixels, sound_df, path_to_video, path_to_audio):
    # Create output directories
    frames_dir = 'output_frames'
    audio_dir = 'output_audio'
    if not os.path.exists(frames_dir):
        os.makedirs(frames_dir)
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    # Read video file
    video = cv2.VideoCapture(path_to_video)

    # Extract frames and save to output directory
    count = 0
    while True:
        success, image = video.read()
        if not success:
            break
        resized_image = cv2.resize(image, frame_pixels)
        filename = f"{frames_dir}/frame{count}.jpg"
        cv2.imwrite(filename, resized_image)
        count += 1

    # Read audio from video file and save to output directory
    clip = mp.VideoFileClip(path_to_video)
    audio = clip.audio
    audio.write_audiofile(path_to_audio)

    # Load audio file and extract desired sound section using provided sound dataframe
    sound = mp.AudioFileClip(path_to_audio)
    start = sound_df['Start'].iloc[0]
    end = sound_df['End'].iloc[0]
    sound_section = sound.subclip(start, end)

    # Save extracted sound section to output directory
    sound_filename = f"{audio_dir}/sound_section.mp3"
    sound_section.write_audiofile(sound_filename)

    print("Frames and audio extracted successfully.")

    
def handle_the_video(path2data: str, modeldir: str):
    # Set up paths for input and output files
    video_path = os.path.join(path2data, "video.mp4")
    audio_path = os.path.join(path2data, "audio.mp3")
    frames_path = os.path.join(path2data, "frames")
    sound_sections_path = os.path.join(path2data, "sound_sections")

    # Extract frames and audio from the video
    frame_pixels = extract_frames(video_path, frames_path)
    sound_df = process_audio(audio_path)

    # Cut frames and audio into desired sections
    cut_frames(frame_pixels, sound_df, video_path, audio_path)

    # Run the trained model on the frames and extract results
    model = load_model(modeldir)
    results = {}
    for i, filename in enumerate(os.listdir(frames_path)):
        filepath = os.path.join(frames_path, filename)
        image = cv2.imread(filepath)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (224, 224))
        image = np.expand_dims(image, axis=0)
        prediction = model.predict(image)
        label = np.argmax(prediction)
        results[i] = label

    # Save the results to a file
    results_path = os.path.join(path2data, "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f)

    print("Video processing complete.")
        
