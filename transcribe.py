from google.cloud import speech_v1p1beta1 as speech, storage
from moviepy.editor import VideoFileClip
import os
import time


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "your-google-creds.json"

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    print(f"Uploading {source_file_name} to bucket {bucket_name}...")
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print("Upload complete.")

def transcribe_gcs(gcs_uri, estimated_duration):
    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",  # Make sure this is a valid BCP-47 language tag
        enable_automatic_punctuation=True
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Transcription started. This may take some time...")
    start_time = time.time()

    while not operation.done():
        elapsed_time = time.time() - start_time
        estimated_remaining_time = max(estimated_duration - elapsed_time, 0)
        print(f"Still processing... Estimated time remaining: {estimated_remaining_time:.2f} seconds")
        time.sleep(30)  # Check every 30 seconds

    print("Fetching transcription results...")
    response = operation.result()

    transcription = ""
    for result in response.results:
        transcription += result.alternatives[0].transcript + "\n"
    
    print("Transcription complete.")
    return transcription

def process_video(video_path, bucket_name):
    print(f"Processing video: {video_path}")
    video = VideoFileClip(video_path)
    estimated_duration = video.duration
    video_name = os.path.basename(video_path)
    audio_path = video_path + ".wav"

    print("Extracting audio from video...")
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, codec='pcm_s16le', fps=16000, ffmpeg_params=["-ac", "1"])
    print("Audio extraction complete.")

    print("Uploading audio to Google Cloud Storage...")
    upload_blob(bucket_name, audio_path, video_name + ".wav")
    gcs_uri = f'gs://{bucket_name}/{video_name}.wav'
    
    transcript = transcribe_gcs(gcs_uri, estimated_duration)

    print("Transcription from Google Cloud Speech-to-Text received.")

    return transcript

def transcribe_folder(folder_path, bucket_name, combined_output_path):
    combined_transcript = ""
    print(f"Starting transcription of videos in folder: {folder_path}")

    for filename in os.listdir(folder_path):
        if filename.endswith(".mp4"):  # Adjust according to your video file extensions
            video_path = os.path.join(folder_path, filename)
            print(f"Starting transcription process for {filename}")
            transcript = process_video(video_path, bucket_name)
            combined_transcript += transcript + "\n\n"
            print(f"Completed transcription for {filename}")
            with open(filename + ".txt", 'w') as file: 
                file.write(transcript)

    print(f"Saving combined transcriptions to {combined_output_path}")
    with open(combined_output_path, 'w') as file:
        file.write(combined_transcript)
    print("All transcriptions saved.")

# Set paths and bucket name
folder_path = 'videos'
bucket_name = 'transcribed_videos'
combined_output_path = 'path_to_combined_transcription_file.txt'

print("Initializing Google Cloud clients...")
# Initialize Google Cloud clients
speech_client = speech.SpeechClient()
storage_client = storage.Client()
print("Clients initialized.")

print("Beginning to process folder...")
transcribe_folder(folder_path, bucket_name, combined_output_path)
print("Folder processing complete.")
