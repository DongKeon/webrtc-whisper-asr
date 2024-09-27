from enum import Enum
import asyncio
import json
import struct
import websockets
from websockets.sync.client import ClientConnection

from websockets.exceptions import ConnectionClosed


#TODO: remove default value and force the proper use of ids for send calls
#check if using await next_message() makes sense in the long run
#how does this behave if the connection ends?

class NetEventType(Enum):
    Invalid = 0
    UnreliableMessageReceived = 1
    ReliableMessageReceived = 2
    ServerInitialized = 3
    ServerInitFailed = 4
    ServerClosed = 5
    NewConnection = 6
    ConnectionFailed = 7
    Disconnected = 8
    FatalError = 100
    Warning = 101
    Log = 102
    ReservedStart = 200
    MetaVersion = 201
    MetaHeartbeat = 202

class NetEventDataType(Enum):
    Null = 0
    ByteArray = 1
    UTF16String = 2

class ConnectionId:
    def __init__(self, id):
        self.id = id

class NetworkEvent:
    def __init__(self, t, con_id, data):
        self._type = t
        self._connection_id = con_id
        self._data = data

    @property
    def raw_data(self):
        return self._data
    
    

    @property
    def message_data(self):
        if not isinstance(self._data, str):
            return self._data
        return None

    @property
    def info(self):
        if isinstance(self._data, str):
            return self._data
        return None

    @property
    def type(self):
        return self._type

    @property
    def connection_id(self):
        return self._connection_id

    def __str__(self):
        output = f"NetworkEvent[NetEventType: ({NetEventType(self._type)}), id: ({self._connection_id.id}), Data: ("
        if isinstance(self._data, str):
            output += self._data
        output += ")]"
        return output
    
    def data_to_text(self):
        return self._data.decode('utf-16-le')

    @staticmethod
    def parse_from_string(str):
        values = json.loads(str)
        data = values['data']
        if data is not None:
            if isinstance(data, str):
                pass
            elif isinstance(data, dict):
                buffer = bytearray(len(data.keys()))
                for i in range(len(buffer)):
                    buffer[i] = data[i]
                data = buffer
            else:
                print("network event can't be parsed: " + str)
                return None
        return NetworkEvent(values['type'], values['connectionId'], data)

    @staticmethod
    def to_string(evt):
        return json.dumps(evt.__dict__)

    @staticmethod
    def from_byte_array(arrin):
        arr = bytearray(arrin)
        type = NetEventType(arr[0])
        data_type = NetEventDataType(arr[1])
        id = struct.unpack('<h', arr[2:4])[0]
        data = None
        if data_type == NetEventDataType.ByteArray:
            length = struct.unpack('<i', arr[4:8])[0]
            data = arr[8:8+length]
        elif data_type == NetEventDataType.UTF16String:
            length = struct.unpack('<i', arr[4:8])[0]
            str_data = arr[8:8+(length*2)]
            data = str_data.decode('utf-16-le')
        elif data_type != NetEventDataType.Null:
            raise ValueError('Message has an invalid data type flag: ' + str(data_type))
        return NetworkEvent(type, ConnectionId(id), data)

    @staticmethod
    def to_byte_array(evt):
        #length always needed for the message header
        type_blen = 4
        if evt._data is None:
            data_type = NetEventDataType.Null
            result = bytearray(type_blen)
        elif isinstance(evt._data, str):
            data_type = NetEventDataType.UTF16String
            encoded_str = evt._data.encode('utf-16-le')
            blen = len(encoded_str)
            result = bytearray(type_blen + 4 + blen)
            result[4:8] = struct.pack('<i', blen//2)
            result[8:] = encoded_str
        else:
            data_type = NetEventDataType.ByteArray
            blen = len(evt._data)
            result = bytearray(type_blen + 4 + blen)
            result[4:8] = struct.pack('<i', blen)
            result[8:] = evt._data
        result[0] = evt._type.value
        result[1] = data_type.value
        result[2:4] = struct.pack('<h', evt.connection_id.id)
        return result
    
class WebsocketNetwork:
    '''
    Limited version of WebsocketNetwork. Can connect to the signaling server and then indirectly connect to
    another client that listens using StartServer / ICall.Listen. 
    '''
    PROTOCOL_VERSION = 2

    def __init__(self):
        self.mSocket : ClientConnection= None 
        self.mRemoteProtocolVersion = None
        self.mHeartbeatReceived = False
        self.event_handlers = []  

    async def start(self, uri):
        self.mSocket = await websockets.connect(uri)
        await self.send_version()

        response = await self.mSocket.recv()
        self.parse_message(response)
        print("Ready to exchange messages")
    
    def register_event_handler(self, handler):
        self.event_handlers.append(handler)  #
        
    async def connect(self, address: str):
        evt = NetworkEvent(NetEventType.NewConnection, ConnectionId(1), address)
        await self.send_network_event(evt)

    async def listen(self, address: str):

        evt = NetworkEvent(NetEventType.ServerInitialized, ConnectionId(-1), address)
        await self.send_network_event(evt)

    async def next_message(self):        
        response = await self.mSocket.recv()
        self.parse_message(response)
    
    async def process_messages(self):
        try:
            while True:
                await self.next_message()
        except ConnectionClosed:
            print("Connection closed")
            
        
    async def shutdown(self):
        #TODO: we should return Disconnected events for all known connections first
        #and connection failed for pending connections
        await self.mSocket.close()

    async def send_version(self):
        msg = bytearray(2)
        msg[0] = NetEventType.MetaVersion.value
        msg[1] = WebsocketNetwork.PROTOCOL_VERSION
        await self.mSocket.send(msg)
    
    async def send_network_event(self, evt):
        msg = NetworkEvent.to_byte_array(evt)
        await self._internal_send(msg)
    
    async def send_text(self, text, connection_id: ConnectionId = ConnectionId(1)):
        text_data = text.encode('utf-16-le')
        # without utf-16-le we are getting a EF BB BF as prefix here.
        # This appears to be an UTF-8 prefix to mark byte order
        # https://en.wikipedia.org/wiki/Byte_order_mark
        
        evt = NetworkEvent(NetEventType.ReliableMessageReceived, connection_id, text_data)
        await self.send_network_event(evt)
    

    async def _internal_send(self, msg):
        await self.mSocket.send(msg)

    def parse_message(self, msg):
        if len(msg) == 0:
            pass
        elif msg[0] == NetEventType.MetaVersion.value:
            if len(msg) > 1:
                self.mRemoteProtocolVersion = msg[1]
                print("Received protocol version " + str(self.mRemoteProtocolVersion))
            else:
                print("Received an invalid MetaVersion header without content.")
        elif msg[0] == NetEventType.MetaHeartbeat.value:
            self.mHeartbeatReceived = True
        else:
            evt = NetworkEvent.from_byte_array(msg)
            self.handle_incoming_event(evt)

    def handle_incoming_event(self, evt: NetworkEvent):
        print("Event " + str(evt))
        for handler in self.event_handlers:
            asyncio.create_task(handler(evt)) 
