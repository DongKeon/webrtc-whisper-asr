import asyncio
import json
import string
from abc import ABC, abstractmethod

from typing import List
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCDataChannel, RTCRtpTransceiver, MediaStreamTrack 
from aiortc.contrib.media import MediaPlayer, MediaRecorder
from aiortc.sdp import candidate_from_sdp

from unity import proc_local_sdp
DATA_CHANNEL_RELIABLE= "reliable"
DATA_CHANNEL_UNRELIABLE= "unreliable"

class TracksObserver(ABC):
    @abstractmethod
    async def on_start(self):
        '''Called when a peer connects and playback is expected to start'''
        pass
    @abstractmethod
    async def on_stop(self):
        '''Called on close'''
        pass

    @abstractmethod
    def on_track(self, track: MediaStreamTrack):
        '''Called several times for each track'''
        pass

        
class CallPeer:
    def __init__(self):
        self.peer = RTCPeerConnection()
        
        self.track_observer : TracksObserver = None
        self.out_video_track : MediaStreamTrack = None
        self.out_audio_track : MediaStreamTrack = None

        self.dc_reliable : RTCDataChannel = None
        self.dc_unreliable : RTCDataChannel = None

        self.inc_video_track : MediaStreamTrack = None
        self.inc_audio_track : MediaStreamTrack = None

        self._observers = []
        # Setup peer connection event handlers
        self.peer.on("track", self.on_track)
        self.peer.on("connectionstatechange", self.on_connectionstatechange)
        self.peer.on("datachannel", self.on_data_channel)

    def attach_track(self, track: MediaStreamTrack):
        if track.kind == "video":
            self.out_video_track = track
        else:
            self.out_audio_track = track

    def on_data_channel(self, datachannel):
        print("received new data channel " + datachannel.label)
        if datachannel.label == DATA_CHANNEL_RELIABLE:
            self.dc_reliable = datachannel
        elif datachannel.label == DATA_CHANNEL_UNRELIABLE:
            self.dc_unreliable = datachannel


    def on_signaling_message(self, observer_function):
        self._observers.append(observer_function)

    async def trigger_on_signaling_message(self, message):
        for observer in self._observers:
            await observer(message)
    
    async def forward_message(self, msg: string):
        print("in msg: "+ msg)
        jobj = json.loads(msg)
        if isinstance(jobj, dict):
            if 'sdp' in jobj:
                await self.peer.setRemoteDescription(RTCSessionDescription(jobj["sdp"], jobj["type"]))
                print("setRemoteDescription done")
                if self.peer.signalingState == "have-remote-offer":
                    await self.create_answer()

            if 'candidate' in jobj:
                str_candidate = jobj.get("candidate")
                if str_candidate == "":
                    print("Empty ice candidate")
                    return
                candidate = candidate_from_sdp(str_candidate)
                candidate.sdpMid = jobj.get("sdpMid")
                candidate.sdpMLineIndex = jobj.get("sdpMLineIndex")
                
                await self.peer.addIceCandidate(candidate)
                print("addIceCandidate done")

    async def on_track(self, track):
        print("Track received:", track.kind)
        if track.kind == "audio":
            self.inc_audio_track = track
        elif track.kind == "video":
            self.inc_video_track = track
        if self.track_observer:
            self.track_observer.on_track(track)

    async def on_connectionstatechange(self):
        print("Connection state changed:", self.peer.connectionState)
        if self.peer.connectionState == "connected":
            if self.track_observer:
                await self.track_observer.on_start()
        elif self.peer.connectionState == "failed":
            #todo: handle this in call
            pass
        elif self.peer.connectionState == "closed":
            if self.track_observer:
                await self.track_observer.on_stop()

    
    def setup_transceivers(self):
        if self.videoTransceiver is not None and self.out_video_track is not None:
            self.videoTransceiver.sender.replaceTrack(self.out_video_track)
            self.videoTransceiver.direction = "sendrecv"
        if self.audioTransceiver is not None and self.out_audio_track is not None:
            self.audioTransceiver.sender.replaceTrack(self.out_audio_track)
            self.audioTransceiver.direction = "sendrecv"

    async def create_offer(self):

        self.dc_reliable = self.peer.createDataChannel(label=DATA_CHANNEL_RELIABLE)
        self.dc_unreliable = self.peer.createDataChannel(label=DATA_CHANNEL_UNRELIABLE)

        self.audioTransceiver = self.peer.addTransceiver("audio", direction="sendrecv") 
        self.videoTransceiver = self.peer.addTransceiver("video", direction="sendrecv")
        self.setup_transceivers()

        offer = await self.peer.createOffer()
        print("Offer created")
        await self.peer.setLocalDescription(offer)
        offer_w_ice = self.sdpToText(self.peer.localDescription.sdp, "offer")
        print(offer_w_ice)
        return offer_w_ice

    def sdpToText(self, sdp, sdp_type):
        proc_sdp = proc_local_sdp(sdp)
        data = {"sdp":proc_sdp, "type": sdp_type}
        text =  json.dumps(data)
        return text

    @staticmethod
    def find_first(media_list : List[RTCRtpTransceiver], kind: str):
        for media in media_list:
            if media.kind == kind:
                return media
        return None 
    
    async def create_answer(self):
        #TODO: we must attach our tracks to the transceiver!!!
        #!!!!
        transceivers = self.peer.getTransceivers()
        if len(transceivers) != 2: 
            #this will likely crash later
            print("Offer side might be incompatible. Expected 2 transceivers but found " + len(transceivers))

        self.videoTransceiver = CallPeer.find_first(transceivers, "video")
        if self.videoTransceiver is None: 
            print("No video transceiver found. The remote side is likely incompatible")

        self.audioTransceiver = CallPeer.find_first(transceivers, "audio")
        if self.audioTransceiver is None: 
            print("No audio transceiver found. The remote side is likely incompatible")
        
        self.setup_transceivers()
            
        answer = await self.peer.createAnswer()
        await self.peer.setLocalDescription(answer)
        text_answer = self.sdpToText(self.peer.localDescription.sdp, "answer")
        await self.trigger_on_signaling_message(text_answer)

    async def set_remote_description(self, sdp, type_):
        description = RTCSessionDescription(sdp, type_)
        await self.peer.setRemoteDescription(description)
        print("Remote description set")

    async def add_ice_candidate(self, candidate):
        await self.peer.addIceCandidate(candidate)
    
    async def dispose(self):
        await self.peer.close()