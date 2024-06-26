from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, ColorClip, CompositeVideoClip
import requests
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
import os
from time import sleep
import threading
import tempfile

class Wav2LipSync:
    def __init__(self, api_key, url="https://api.synclabs.so/lipsync", model="wav2lip++", credentials_path="credentials.json", crop_video = False):
        self.api_key = api_key
        self.url = url
        self.model = model
        self.credentials_path = credentials_path
        self.crop_video = crop_video

    def upload_file_to_drive(self, file_path):
        SCOPES = ['https://www.googleapis.com/auth/drive']
        SERVICE_ACCOUNT_FILE = self.credentials_path

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

    def get_direct_download_link(self, file_id):
        SCOPES = ['https://www.googleapis.com/auth/drive']
        SERVICE_ACCOUNT_FILE = self.credentials_path

        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)

        file = service.files().get(fileId=file_id, fields='webContentLink').execute()
        
        return file.get('webContentLink')

    def upload_file(self, path):
        link = self.upload_file_to_drive(path)
        print(f'File {path} upload completed')
        return link

    def get_link(self, path):
        return self.get_direct_download_link(self.upload_file(path).split('/')[-2])

    def __call__(self, file_path, audio_path, output_path=None):
        return self.wav2lip(file_path, audio_path, output_path)
    
    def wav2lip(self, file_path, audio_path, output_path=None):
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_clip = ImageClip(file_path)
            audio_clip = AudioFileClip(audio_path)

            final_video = image_clip.set_audio(None).set_duration(audio_clip.duration)
            video_path = tempfile.NamedTemporaryFile(suffix='.mp4').name

            final_video.write_videofile(video_path, codec='libx264', fps=24)
            final_video.close()
        elif file_path.lower().endswith(('.mp4', '.avi', '.mov')): video_path = file_path
        else: raise ValueError("Unsupported file format")

        if self.crop_video:
            video = VideoFileClip(video_path)
            video_path = tempfile.NamedTemporaryFile(suffix='.mp4').name
            width, height = video.size
            empty_clip = ColorClip(size=(width, height * 3), color=(0, 0, 0)).set_duration(video.duration)
            cropped_video = CompositeVideoClip([empty_clip.set_pos(('center', 'top')), video.set_pos(('center', 'bottom'))])
            cropped_video.write_videofile(video_path, codec='libx264', fps=video.fps)
        
        audio_thread = threading.Thread(target=lambda: setattr(audio_thread, 'result', self.get_link(audio_path)))
        video_thread = threading.Thread(target=lambda: setattr(video_thread, 'result', self.get_link(video_path)))

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
            "model": self.model,
            "audioUrl": audio_direct_link,
            "videoUrl": video_direct_link
        }
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        response = requests.request("POST", self.url, json=payload, headers=headers)

        id = response.json().get('id')
        print(f'Lip ID: {id}')

        time = 0
        status = "OKAY"

        while status not in ["COMPLETED", "ERROR"]:
            get = requests.request("GET", f'{self.url}/{id}', headers=headers)
            status = get.json().get('status')
            print(f"Lip Status: {status} Time: {time}", end="\r")
            time += 1
            sleep(1)

        video_url = get.json().get('videoUrl')

        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp.write(requests.get(video_url).content)
        temp_path = temp.name

        print(f'Lip result: {video_url} Temp: {temp_path}')

        video = VideoFileClip(temp_path)

        if output_path is None:
            output_path = tempfile.NamedTemporaryFile(suffix='.mp4').name

        if self.crop_video:
            cropped_video = video.crop(y1=video.h * 2 // 3, y2=0)
            cropped_video.write_videofile(output_path, codec='libx264', fps=24)
            cropped_video.close()
        else:
            video.write_videofile(output_path, codec='libx264', fps=video.fps)

        temp.close()
        os.unlink(temp.name)
        video.close()

        return output_path