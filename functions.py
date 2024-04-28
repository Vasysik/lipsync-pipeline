import moviepy.editor as mp
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
import os
from time import sleep
import threading
import numpy as np
from PIL import Image

def upload_file_to_drive(file_path, credentials_path):
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = credentials_path

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)

    file_metadata = {
        'name': os.path.basename(file_path),
    }
    media = MediaFileUpload(file_path, resumable=True)  
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    service.permissions().create(fileId=file['id'], body=permission).execute()

    return file.get('webViewLink')

def get_direct_download_link(file_id, credentials_path):
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = credentials_path

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)

    file = service.files().get(fileId=file_id, fields='webContentLink').execute()
    
    return file.get('webContentLink')

def upload_file(path, credentials_path):
    link = upload_file_to_drive(path, credentials_path)
    print(f'File {path} upload completed')
    return link

def get_link(path, credentials_path):
    return get_direct_download_link(upload_file(path, credentials_path).split('/')[-2], credentials_path)

def wav2lip(image_path, audio_path, output_path, api_key, url, credentials_path):
    original_image = Image.open(image_path)
    width, height = original_image.size
    new_height = height * 3
    new_image = Image.new("RGB", (width, new_height), (255, 255, 255))
    new_image.paste(original_image, (0, new_height - height))

    image_array = np.array(new_image)
    image_clip = mp.ImageClip(image_array)
    audio_clip = mp.AudioFileClip(audio_path)

    final_video = image_clip.set_audio(None).set_duration(audio_clip.duration)

    final_video.write_videofile(output_path, codec='libx264', fps=24)

    audio_thread = threading.Thread(target=lambda: setattr(audio_thread, 'result', get_link(audio_path, credentials_path)))
    video_thread = threading.Thread(target=lambda: setattr(video_thread, 'result', get_link(output_path, credentials_path)))

    audio_thread.start()
    video_thread.start()

    audio_thread.join()
    video_thread.join()
    
    print("Both uploads completed")
    audio_direct_link = audio_thread.result
    print("Audio link:", audio_direct_link)
    video_direct_link = video_thread.result
    print("Video link:", video_direct_link)

    payload = {
        "model": "wav2lip++",
        "audioUrl": audio_direct_link,
        "videoUrl": video_direct_link
    }
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    id = response.json().get('id')
    print(id)

    time = 0
    status = "OKAY"

    while status != "COMPLETED":
        get = requests.request("GET", f'{url}/{id}', headers=headers)
        status = get.json().get('status')
        print(f"{status} {time}", end="\r")
        time += 1
        sleep(1)

    video_url = get.json().get('videoUrl')
    print(video_url)

    video = mp.VideoFileClip(video_url)
    cropped_video = video.crop(y1=video.h * 2 // 3, y2=0)
    cropped_video.write_videofile(output_path, codec='libx264', fps=24)

    return output_path

image_path = 'pups.png'
audio_path = 'wdw.mp3'
output_path = 'out.mp4'

api_key = 'f5a97ebb-c150-48be-a35c-9010ba69e0ec'
url = "https://api.synclabs.so/lipsync"
credentials_path = "credentials.json"

print(wav2lip(image_path, audio_path, output_path, api_key, url, credentials_path))
