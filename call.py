from websocket_network import WebsocketNetwork, NetworkEvent, NetEventType
from aiortc import MediaStreamTrack

from call_peer import CallPeer, TracksObserver

'''
Prototype Call implementation similar to Unity ICall and BrowserCall for web. 
* So it will send a video based on a file and will write the received video to a file
    (see CallPeer init below)
* Only 1 peer
* The remote side must already wait for an incoming call
'''
class Call:
    def __init__(self, uri, track_observer: TracksObserver = None):
        self.network : WebsocketNetwork = None
        self.uri = uri
        self.in_signaling = False
        self.listening = False

        self.peer = CallPeer()
        self.peer.track_observer = track_observer
        
        self.peer.on_signaling_message(self.on_peer_signaling_message)
        self.connection_id = None
        #todo: event handler to deal with offer,answer and ice candidates
        #self.peer.register_event_handler(self.peer_signaling_event_handler)
    def attach_track(self, track: MediaStreamTrack):
        if track.kind == "video":
            self.out_video_track = track
        else:
            self.out_audio_track = track
        self.peer.attach_track(track)
    async def on_peer_signaling_message(self, msg: str):
        print("sending " + msg)
        await self.network.send_text(msg, self.connection_id)

    async def listen(self, address):
        self.network = WebsocketNetwork()
        self.network.register_event_handler(self.signaling_event_handler)
        #connect to signaling server itself
        await self.network.start(self.uri)
        #connect indirectly to unity client through the server
        await self.network.listen(address)
        self.in_signaling = True
        #loop and wait for messages.
        #they are returned via the event handler
        await self.network.process_messages()

    async def call(self, address):
        self.network = WebsocketNetwork()
        self.network.register_event_handler(self.signaling_event_handler)
        #connect to signaling server itself
        await self.network.start(self.uri)
        #connect indirectly to unity client through the server
        await self.network.connect(address)
        self.in_signaling = True
        #loop and wait for messages.
        #they are returned via the event handler
        await self.network.process_messages()
        
    def shutdown(self, reason = ""):
        print("Shutting down. Reason: " + reason)
        self.in_signaling = False
        #todo: clean shutdown
        #self.network.shutdown()

    async def handle_message(self, message):
        print(f"forwarding signaling message from peer: {message}")
        await self.network.send_text(message)

    
    async def signaling_event_handler(self, evt: NetworkEvent):    
        print(f"Received event of type {evt.type}")
        if evt.type == NetEventType.NewConnection:
            print("NewConnection event")
            self.connection_id = evt.connection_id
            #TODO: we need an event handler to 
            #manage all other signaling messages anway. 
            #no need to give the offer special treatmeant via
            #its own call
            if self.listening == False:
                offer = await self.peer.create_offer()
                print("sending : " + offer)
                await self.network.send_text(offer)

        elif evt.type == NetEventType.ConnectionFailed:
            print("ConnectionFailed event")
            self.shutdown("ConnectionFailed event from signaling")
        elif evt.type == NetEventType.ServerInitialized:
            self.listening = True
        elif evt.type == NetEventType.ServerInitFailed:
            #
            print("Listening failed")
            
            

        elif evt.type == NetEventType.ReliableMessageReceived:
            msg : str = evt.data_to_text()
            await self.peer.forward_message(msg)
    
    async def dispose(self):
        if self.peer:
            await self.peer.dispose()

