import os
import asyncio
# from aiortc.contrib.media import MediaPlayer, MediaRecorder
from customMediaRecorder import CustomMediaRecorder
from dotenv import load_dotenv

from call import Call
from call_peer import TracksObserver

load_dotenv()

# Implementing the interface
class MyTracksHandler(TracksObserver):

    def __init__(self, filename):
        self.recorder = CustomMediaRecorder(filename)

    async def on_start(self):
        print("Starting recording ...")
        await self.recorder.start()

    async def on_stop(self):
        print("Stopping recording")
        await self.recorder.stop()
        print("Recording stopped")

    def on_track(self, track):
        print(f"add track: {track.id}")
        self.recorder.addTrack(track)
    
def main(server_ip, address):
    uri = f'ws://{server_ip}:12776/conferenceapp'

    call  = Call(uri, MyTracksHandler("inc.wav"))

    loop = asyncio.get_event_loop()
    
    try:
        loop.run_until_complete(call.call(str(address)))
    except KeyboardInterrupt:
        pass
    finally:        
        print("Shutting down...")
        loop.run_until_complete(call.dispose())
        print("shutdown complete.")

if __name__ == "__main__":
    server_ip = '127.0.0.1'
    address = '1'
    main(server_ip, address)
