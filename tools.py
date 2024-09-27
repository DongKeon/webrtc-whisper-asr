
from aiortc import VideoStreamTrack
from aiortc.contrib.media import MediaPlayer


def filter_vp8_codec(sdp_data):
    lines = sdp_data.split('\r\n')
    filtered_lines = []
    
    video_section = False
    for line in lines:
        # Keeping non-media lines
        if not line.startswith('m='):
            if video_section:
                if line.startswith('a=rtpmap:') and 'VP8' in line:
                    filtered_lines.append(line)
                    continue  # Skip other codec lines
                elif line.startswith('a=rtpmap:') and 'VP8' not in line:
                    continue  # Skip other codec lines
                elif line.startswith('a=rtcp-fb:') and any(codecs in line for codecs in ['97', '98', '99', '100', '101', '102']):
                    continue  # Skip other codec lines
                elif line.startswith('a=fmtp:') and any(codecs in line for codecs in ['97', '98', '99', '100', '101', '102']):
                    continue  # Skip other codec lines
            filtered_lines.append(line)
        else:
            if 'audio' in line or 'application' in line:
                filtered_lines.append(line)
                video_section = False
            elif 'video' in line:
                video_section = True
                # Keeping only the VP8 codec (97)
                filtered_lines.append('m=video 9 UDP/TLS/RTP/SAVPF 97')

    # Reconstructing the SDP
    filtered_sdp = '\r\n'.join(filtered_lines)

    return filtered_sdp

class CameraStreamTrack(VideoStreamTrack):
    """
    A video stream track that captures video from the camera.
    """
    def __init__(self):
        super().__init__() 
        
        #self.player = MediaPlayer('/dev/video0', format='v4l2', options={'video_size': '640x480'})
        self.player = MediaPlayer('video.mp4')

    async def recv(self):
        frame = await self.player.video.recv()
        return frame