import os
import base64
import pandas as pd
import json
import xml.etree.ElementTree as ET
from docx import Document
import win32com.client as win32
import speech_recognition as sr
from moviepy.editor import VideoFileClip
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredPowerPointLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pprint import pprint

class DataLoader:
    def __init__(self, folder_path, chunk_size=100, chunk_overlap=10):
        self.folder_path = folder_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_text_file(self, file_path):
        loader = TextLoader(file_path, encoding="utf-8")
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunks = text_splitter.split_documents(documents)
        return [
            {
                "chunk_no": int(idx),
                "text": chunk.page_content,
                "path": file_path,
                "file_type": "text",
                "media_type": "text"
            }
            for idx, chunk in enumerate(chunks)
        ]


    def process_audio_file(self, file_path):
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(file_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
            chunks = [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

            return [
                {
                    "chunk_no": int(idx),
                    "text": chunk,
                    "path": file_path,
                    "file_type": "audio",
                    "media_type": "text"
                }
                for idx, chunk in enumerate(chunks)
            ]
        except Exception as e:
            print(f"Error processing audio file {file_path}: {e}")
            return None
        
    def process_image_file(self, file_path):
        try:
            with open(file_path, 'rb') as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            return [{
                "path": file_path,
                "file_type": "image",
                "image": image_base64,
                "media_type": "image"
            }]
        except Exception as e:
            print(f"Error processing image file {file_path}: {e}")
            return None


    def process_video_file(self, file_path, frame_interval=5, compression_quality=50, resize_factor=0.7):

            video_data = []

            if frame_interval <= 0:
                print(f"Error: frame_interval must be greater than 0. Received frame_interval={frame_interval}.")
                return video_data

            try:
                video = VideoFileClip(file_path)
                audio_path = file_path.replace(os.path.splitext(file_path)[1], ".wav")
                
                try:
                    video.audio.write_audiofile(audio_path)
                    audio_data = self.process_audio_file(audio_path)
                    if audio_data:
                        video_data.extend(audio_data)
                except Exception as e:
                    print(f"Error processing audio file {audio_path}: {e}")

                for i, frame in enumerate(video.iter_frames(fps=1.0 / frame_interval)):
                    pil_image = Image.fromarray(frame)
                    
                    if resize_factor < 1.0:
                        new_size = (int(pil_image.width * resize_factor), int(pil_image.height * resize_factor))
                        pil_image = pil_image.resize(new_size, Image.LANCZOS)
                    buffered = io.BytesIO()
                    pil_image.save(buffered, format="JPEG", quality=compression_quality)
                    frame_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    video_data.append({
                        "chunk_no": i,
                        "image": frame_base64,
                        "path": file_path,
                        "file_type": "video_frame",
                        "media_type": "image"
                    })

            except Exception as e:
                print(f"Error processing video file {file_path}: {e}")
            
            return video_data

    def process_file(self, file_path):
        extension = os.path.splitext(file_path)[1].lower()
        if extension == '.txt':
            return self.process_text_file(file_path)
        elif extension in ['.wav', '.mp3']:
            return self.process_audio_file(file_path)
        elif extension in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
            return self.process_image_file(file_path)
        elif extension in ['.mp4', '.avi', '.mov', '.wmv']:
            return self.process_video_file(file_path)
        else:
            return None

    def load_data(self):
        all_data = []
        for root, dirs, files in os.walk(self.folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                processed_data = self.process_file(file_path)
                if processed_data is not None:
                    all_data.extend(processed_data)
        return all_data



