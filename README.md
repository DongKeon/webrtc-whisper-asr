# webrtc-whisper-asr

WebRTC-based real-time audio streaming with Faster Whisper ASR integration for live speech-to-text transcription.

## Overview

This repository contains the Python client part of a WebRTC-based audio streaming solution with real-time Automatic Speech Recognition (ASR) using Faster Whisper. The client receives audio streams and processes them for real-time transcription.

**Note:** The WebSocket signaling server used in this project is from [awrtc_signaling](https://github.com/because-why-not/awrtc_signaling) and is not included in this repository.

## Features

- WebRTC-based audio receiving
- Real-time audio processing (16kHz sampling rate, mono channel)
- Faster Whisper-based real-time ASR
- Customized aiortc implementation

## Prerequisites

- Python 3.8 (recommended)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/DongKeon/webrtc-whisper-asr.git
   cd webrtc-whisper-asr
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

In `run.py`, set the `server_ip` and `address` variables:

```python
server_ip = 'your_server_ip_here'
address = 'your_chat_room_number_here'
```

## Usage

Run the Python client:

```
python run.py
```

## Customization

- The `customMediaRecorder.py` file is recommended for implementing custom audio processing logic.
- The `aiortc/contrib/media.py` file contains the audio stream settings, which can be adjusted as needed.

## Notes

- Ensure that a compatible WebRTC audio streaming source is connected before running this client.
- The `server_ip` in `run.py` should match the IP of your WebSocket signaling server.
- The `address` in `run.py` should match the chat room number used by the audio source.

## Contact
- dongkeon@gm.gist.ac.kr

