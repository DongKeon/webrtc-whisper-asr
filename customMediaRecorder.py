import numpy as np
from scipy.io import wavfile
from aiortc.contrib.media import MediaRecorder
from whisper_online import FasterWhisperASR, OnlineASRProcessor
import os

class CustomMediaRecorder(MediaRecorder):
    def __init__(self, filename, language="ko", model="large-v3", save_wav=False):
        super().__init__(filename)
        self.asr = FasterWhisperASR(language, model)
        self.online = OnlineASRProcessor(self.asr)
        self.buffer = np.array([], dtype=np.float32)
        self.sample_rate = 16000
        self.chunk_size = self.sample_rate

        self.save_wav = save_wav
        if self.save_wav:
            self.wav_buffer = np.array([], dtype=np.float32)
            self.wav_filename = "tmp_dir/output.wav"
            if os.path.exists(self.wav_filename):
                os.remove(self.wav_filename)

    def custom_audio_process(self, audioframe: np.ndarray):
        audio_float = audioframe.astype(np.float32) / 32767.0
        self.buffer = np.concatenate([self.buffer, audio_float])
        
        if self.save_wav:
            self.wav_buffer = np.concatenate([self.wav_buffer, audio_float])
        
        # Process audio in chunks of 1 second (16000 samples at 16kHz)
        while len(self.buffer) >= self.chunk_size:
            chunk = self.buffer[:self.chunk_size]
            self.buffer = self.buffer[self.chunk_size:]
            
            # Process the chunk
            self.online.insert_audio_chunk(chunk)
            result = self.online.process_iter()
            # Print the result if there's transcribed text
            if result[2]:
                print(f"{result[0]:.2f} - {result[1]:.2f}: {result[2]}")

    def save_wav(self):
        if len(self.wav_buffer) > 0:
            # Convert float audio to int16
            wav_data = (self.wav_buffer * 32767).astype(np.int16)
            #stereo_data = self.wav_buffer.reshape(-1, 2)
            #wav_data = (stereo_data * 32767).astype(np.int16)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.wav_filename), exist_ok=True)
            
            # Save the WAV file
            wavfile.write(self.wav_filename, self.sample_rate, wav_data)
            print(f"WAV file saved as {self.wav_filename}")
        else:
            print("No audio data to save")

    async def stop(self):
        await super().stop()
        if self.save_wav:
            self.save_wav()  
