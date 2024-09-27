from enum import Enum
import time
import asyncio
import json
import os
from websocket_network import WebsocketNetwork, NetworkEvent, NetEventType
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

from aiortc.contrib.media import MediaRecorder, MediaPlayer

from tools import filter_vp8_codec
from aiortc.sdp import candidate_from_sdp
from dotenv import load_dotenv
load_dotenv()

uri = os.getenv('SIGNALING_URI', 'ws://192.168.1.3:12776')
address = os.getenv('ADDRESS', "abc123")



recording = True
sending = True



inc_video_track = None
inc_audio_track = None

print(uri)
print(address)

network : WebsocketNetwork = None

peer = RTCPeerConnection()
@peer.on("connectionstatechange")
def on_connectionstatechange():
    print("connectionstatechange:", peer.connectionState)

@peer.on("track")
def on_track(track):
    global inc_video_track
    global inc_audio_track
    global recording
    print("track:", track.kind)
    if track.kind == "video":
        inc_video_track = track
        asyncio.ensure_future(proc_video(track))
    else:
        inc_audio_track = track
    
    if inc_audio_track and inc_video_track:
        print("got both a video and audio track")
        if recording:
            asyncio.ensure_future(start_recording(inc_audio_track, inc_video_track))
            

async def proc_video(track):
    last_fps_print = time.time()
    frame_counter = 0

    while True:
        if peer.connectionState == 'new' or peer.connectionState == "connecting":
            await asyncio.sleep(0.1)
            continue

        elif peer.connectionState != "connected":
            print("Peer state neither connecting nor connected. Exiting proc_video")
            break

        frame = await track.recv()
        frame_counter += 1

        elapsed_time = time.time() - last_fps_print
        if elapsed_time >= 1.0:  # If a second has passed
            fps = frame_counter / elapsed_time
            print(f'FPS: {fps} {frame.width}x{frame.height} format: {frame.format}')
            frame_counter = 0
            last_fps_print = time.time()
        




global dc1
dc1 = None
global dc2
dc2 = None

global setting_remote
setting_remote = False

global message_buffer
message_buffer = []

def proc_local_sdp(sdp: str):

    sdp_res = sdp.replace("a=extmap:2 urn:ietf:params:rtp-hdrext:ssrc-audio-level", "a=extmap:3 urn:ietf:params:rtp-hdrext:ssrc-audio-level")
    #this forces VP8.
    #sdp_res = filter_vp8_codec(sdp_res)
    return sdp_res



def append_candidate(sdp, candidate):
    sdp += 'a={}\r\n'.format(candidate)
    return sdp

def convert_json_to_sdp(json_messages):
    for msg in json_messages:
        if 'sdp' in msg:
            sdp_buffer = msg['sdp']
        if 'candidate' in msg:
            sdp_buffer = append_candidate(sdp_buffer, msg['candidate'])
    return sdp_buffer

async def create_offer():
    global dc1
    global dc2
    global sending
    dc1 = peer.createDataChannel(label="reliable")
    dc2 = peer.createDataChannel(label="unreliable")

    @dc1.on("message")
    def on_message(message):
        print("dc1", message)
    @dc2.on("message")
    def on_message(message):
        print("dc2", message)

    audioTransceiver = peer.addTransceiver("audio", direction="sendrecv") 
    #this is still broken
    videoTransceiver = peer.addTransceiver("video", direction="sendrecv")
    if sending:
        player = MediaPlayer('video.mp4')
        videoTransceiver.sender.replaceTrack(player.video)
        audioTransceiver.sender.replaceTrack(player.audio)

    offer = await peer.createOffer()
    await peer.setLocalDescription(offer)

    sdp = proc_local_sdp(peer.localDescription.sdp)
    print(sdp)
    data = {"sdp":sdp, "type":"offer"}
    offer_w_ice =  json.dumps(data)
    print(offer_w_ice)
    return offer_w_ice

async def my_event_handler(evt: NetworkEvent):
    
    print(f"Received event of type {evt.type}")
    if evt.type == NetEventType.NewConnection:
        # got connected. For now we assume the remote side is already in the waiting state
        # this means we can just send an offer

        #test_offer = '{"sdp":"v=0\r\no=- 2871846415274796188 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0 1 2\r\na=extmap-allow-mixed\r\na=msid-semantic: WMS\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111 63 9 102 0 8 13 110 126\r\nc=IN IP4 0.0.0.0\r\na=rtcp:9 IN IP4 0.0.0.0\r\na=ice-ufrag:DCj/\r\na=ice-pwd:eGcniT3aIT51cU6E1xfx8K9F\r\na=ice-options:trickle\r\na=fingerprint:sha-256 90:9C:9B:F4:71:B8:9F:6E:BA:D9:5C:84:79:B0:30:D5:83:29:57:3C:FD:56:AE:FD:D8:2E:38:26:A9:9B:A3:9B\r\na=setup:actpass\r\na=mid:0\r\na=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level\r\na=extmap:2 http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time\r\na=extmap:3 http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01\r\na=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid\r\na=recvonly\r\na=rtcp-mux\r\na=rtpmap:111 opus/48000/2\r\na=rtcp-fb:111 transport-cc\r\na=fmtp:111 minptime=10;useinbandfec=1\r\na=rtpmap:63 red/48000/2\r\na=fmtp:63 111/111\r\na=rtpmap:9 G722/8000\r\na=rtpmap:102 ILBC/8000\r\na=rtpmap:0 PCMU/8000\r\na=rtpmap:8 PCMA/8000\r\na=rtpmap:13 CN/8000\r\na=rtpmap:110 telephone-event/48000\r\na=rtpmap:126 telephone-event/8000\r\nm=video 9 UDP/TLS/RTP/SAVPF 96 97 98 99 100 101 35 36 37 38 39 40 41 42 127 103 104 43\r\nc=IN IP4 0.0.0.0\r\na=rtcp:9 IN IP4 0.0.0.0\r\na=ice-ufrag:DCj/\r\na=ice-pwd:eGcniT3aIT51cU6E1xfx8K9F\r\na=ice-options:trickle\r\na=fingerprint:sha-256 90:9C:9B:F4:71:B8:9F:6E:BA:D9:5C:84:79:B0:30:D5:83:29:57:3C:FD:56:AE:FD:D8:2E:38:26:A9:9B:A3:9B\r\na=setup:actpass\r\na=mid:1\r\na=extmap:14 urn:ietf:params:rtp-hdrext:toffset\r\na=extmap:2 http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time\r\na=extmap:13 urn:3gpp:video-orientation\r\na=extmap:3 http://www.ietf.org/id/draft-holmer-rmcat-transport-wide-cc-extensions-01\r\na=extmap:5 http://www.webrtc.org/experiments/rtp-hdrext/playout-delay\r\na=extmap:6 http://www.webrtc.org/experiments/rtp-hdrext/video-content-type\r\na=extmap:7 http://www.webrtc.org/experiments/rtp-hdrext/video-timing\r\na=extmap:8 http://www.webrtc.org/experiments/rtp-hdrext/color-space\r\na=extmap:4 urn:ietf:params:rtp-hdrext:sdes:mid\r\na=extmap:10 urn:ietf:params:rtp-hdrext:sdes:rtp-stream-id\r\na=extmap:11 urn:ietf:params:rtp-hdrext:sdes:repaired-rtp-stream-id\r\na=recvonly\r\na=rtcp-mux\r\na=rtcp-rsize\r\na=rtpmap:96 VP8/90000\r\na=rtcp-fb:96 goog-remb\r\na=rtcp-fb:96 transport-cc\r\na=rtcp-fb:96 ccm fir\r\na=rtcp-fb:96 nack\r\na=rtcp-fb:96 nack pli\r\na=rtpmap:97 rtx/90000\r\na=fmtp:97 apt=96\r\na=rtpmap:98 VP9/90000\r\na=rtcp-fb:98 goog-remb\r\na=rtcp-fb:98 transport-cc\r\na=rtcp-fb:98 ccm fir\r\na=rtcp-fb:98 nack\r\na=rtcp-fb:98 nack pli\r\na=fmtp:98 profile-id=0\r\na=rtpmap:99 rtx/90000\r\na=fmtp:99 apt=98\r\na=rtpmap:100 VP9/90000\r\na=rtcp-fb:100 goog-remb\r\na=rtcp-fb:100 transport-cc\r\na=rtcp-fb:100 ccm fir\r\na=rtcp-fb:100 nack\r\na=rtcp-fb:100 nack pli\r\na=fmtp:100 profile-id=2\r\na=rtpmap:101 rtx/90000\r\na=fmtp:101 apt=100\r\na=rtpmap:35 VP9/90000\r\na=rtcp-fb:35 goog-remb\r\na=rtcp-fb:35 transport-cc\r\na=rtcp-fb:35 ccm fir\r\na=rtcp-fb:35 nack\r\na=rtcp-fb:35 nack pli\r\na=fmtp:35 profile-id=1\r\na=rtpmap:36 rtx/90000\r\na=fmtp:36 apt=35\r\na=rtpmap:37 VP9/90000\r\na=rtcp-fb:37 goog-remb\r\na=rtcp-fb:37 transport-cc\r\na=rtcp-fb:37 ccm fir\r\na=rtcp-fb:37 nack\r\na=rtcp-fb:37 nack pli\r\na=fmtp:37 profile-id=3\r\na=rtpmap:38 rtx/90000\r\na=fmtp:38 apt=37\r\na=rtpmap:39 AV1/90000\r\na=rtcp-fb:39 goog-remb\r\na=rtcp-fb:39 transport-cc\r\na=rtcp-fb:39 ccm fir\r\na=rtcp-fb:39 nack\r\na=rtcp-fb:39 nack pli\r\na=rtpmap:40 rtx/90000\r\na=fmtp:40 apt=39\r\na=rtpmap:41 AV1/90000\r\na=rtcp-fb:41 goog-remb\r\na=rtcp-fb:41 transport-cc\r\na=rtcp-fb:41 ccm fir\r\na=rtcp-fb:41 nack\r\na=rtcp-fb:41 nack pli\r\na=fmtp:41 profile=1\r\na=rtpmap:42 rtx/90000\r\na=fmtp:42 apt=41\r\na=rtpmap:127 red/90000\r\na=rtpmap:103 rtx/90000\r\na=fmtp:103 apt=127\r\na=rtpmap:104 ulpfec/90000\r\na=rtpmap:43 flexfec-03/90000\r\na=rtcp-fb:43 goog-remb\r\na=rtcp-fb:43 transport-cc\r\na=fmtp:43 repair-window=10000000\r\nm=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\nc=IN IP4 0.0.0.0\r\na=ice-ufrag:DCj/\r\na=ice-pwd:eGcniT3aIT51cU6E1xfx8K9F\r\na=ice-options:trickle\r\na=fingerprint:sha-256 90:9C:9B:F4:71:B8:9F:6E:BA:D9:5C:84:79:B0:30:D5:83:29:57:3C:FD:56:AE:FD:D8:2E:38:26:A9:9B:A3:9B\r\na=setup:actpass\r\na=mid:2\r\na=sctp-port:5000\r\na=max-message-size:262144\r\n","type":"offer"}'
        test_offer = await create_offer()
        print("sending : " + test_offer)
        await network.send_text(test_offer)

    if evt.type == NetEventType.ReliableMessageReceived:
        # we received a message from the other end. The other side will send a random number in case we need to negotiate
        # who is suppose to send an offer. 
        # all other messages should be answer & ice candidates
        global message_buffer
        msg : str = evt.data_to_text()
        print("in msg: "+ msg)
        global setting_remote
        if 'sdp' in msg and setting_remote == False:
            setting_remote = True
            json_msg = json.loads(msg)
            await peer.setRemoteDescription(RTCSessionDescription(json_msg["sdp"], json_msg["type"]))
        if 'candidate' in msg:
            candidate_dict = json.loads(msg)

            str_candidate = candidate_dict.get("candidate")
            if str_candidate == "":
                print("Empty ice candidate")
                return
            candidate = candidate_from_sdp(str_candidate)
            candidate.sdpMid = candidate_dict.get("sdpMid")
            candidate.sdpMLineIndex = candidate_dict.get("sdpMLineIndex")
            
            await peer.addIceCandidate(candidate)



async def dummy_task():
    while True:
        await asyncio.sleep(10) 

async def run_signaling():
    global network
    network = WebsocketNetwork()
    network.register_event_handler(my_event_handler)
    #connect to signaling server itself
    await network.start(uri)
    #connect indirectly to unity client through the server
    await network.connect(address)
    await network.process_messages()
    
    

recorder = None

async def start_recording(audio_track, video_track):
    global recorder
    # Create a MediaRecorder instance
    recorder = MediaRecorder("rec.mp4")

    # Add the audio and video tracks to the recorder
    recorder.addTrack(audio_track)
    recorder.addTrack(video_track)

    # Start recording
    await recorder.start()
    print("recording started ....")


async def stop_recording():
    global recorder
    if recorder:
        # Start recording
        await recorder.stop()
        print("recording stop ...")


async def main():
    
    task1 = asyncio.ensure_future(run_signaling())

    #place holder for other task
    task2 = asyncio.ensure_future(dummy_task())
    await asyncio.gather(task1, task2)

if __name__ == "__main__":
    print("Start")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:        
        print("Shutting down...")
        loop.run_until_complete(stop_recording())
        print("stop loop ...")
        loop.close()
    



