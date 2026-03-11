import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import socket

server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
Gst.init(None)

IP_CAM = "10.110.246.66" # edit here
PORT_NO = 9999

def navigation_probe_callback(pad, info, user_data):
    event = info.get_event()
    if event.type == Gst.EventType.NAVIGATION:
        # Check if it's a mouse button press
        struct = event.get_structure()
        event_type = struct.get_string("event")
        
        if event_type == "mouse-button-press":
            _, x = struct.get_double("pointer_x")
            _, y = struct.get_double("pointer_y")
            server.sendto(f"{x},{y}".encode(),(IP_CAM,PORT_NO))
        elif event_type == "key-press":
            key_name = struct.get_string("key")
            if key_name == "q":
                print(f"you pressed {key_name}, RTL-ing")
                server.sendto(f"{key_name}".encode(),(IP_CAM,PORT_NO))

    return Gst.PadProbeReturn.OK
pipeline_str = "rtspsrc location=rtsp://10.110.246.66:8554/my_stream latency=0 ! rtph264depay ! h264parse ! avdec_h264 skip-frame=1 ! videoconvert ! autovideosink name=sink sync=false"
#pipeline_str = "rtspsrc location=rtsp://10.228.158.66:8554/my_stream latency=0 ! rtph264depay ! h264parse ! decodebin ! videoconvert ! autovideosink name=sink sync=true"
pipeline = Gst.parse_launch(pipeline_str)

sink = pipeline.get_by_name("sink")
sink_pad = sink.get_static_pad("sink")
sink_pad.add_probe(Gst.PadProbeType.EVENT_UPSTREAM, navigation_probe_callback,None)
pipeline.set_state(Gst.State.PLAYING)
loop = GLib.MainLoop()

try:
   loop.run()
   print("running")
except KeyboardInterrupt:
   pass
pipeline.set_state(Gst.State.NULL)