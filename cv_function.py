import cv2
import subprocess
import threading
import socket
import tracking_stuff



# a function that i import

# overall goal
# 1.) click 'c' key
# 2.) model does inference and outputs rtsp stream
# 3.) laptop receives rtsp stream, sends udp coord of bbox
# 4.) as soon as rpi receives bbox, it goes towards the bbox

# function needs to come in after i click 'c' key, it only stops when function outputs a bbox coordinate
# given a frame, output rtsp stream, function only ends when bbox coordinate is returned

async def cv_stuff(model,rtsp_in,rtsp_out,drone,trackHeight,moveForward):

    UDP_IP = "10.110.246.66" # your rpi ip
    UDP_PORT = 9999

    # threaded udp port listener, since listening would pause for the whole script
    # start another thread to listen at the same time
    class Getxy:
        def __init__(self,UDP_IP,UDP_PORT):
            self.x = -1
            self.y = -1
            self.client = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            self.client.bind((UDP_IP,UDP_PORT))
            threading.Thread(target=self.UDP_listening,daemon=True).start()
        def UDP_listening(self):
            while True:
                data,addr = self.client.recvfrom(1024)
                string = data.decode()
                list_xy = string.split(",")
                self.x=int(float(list_xy[0]))
                self.y=int(float(list_xy[1]))
        def get_xy_values(self):
            if (self.x > 0 or self.y > 0):
                tempx=self.x
                tempy=self.y
                self.x = -1
                self.y = -1
                return (tempx,tempy)

    # Threaded Camera Reader to skip buffered frames
    # cos if you call .read for every loop in the while loop, it actually stores a buffer if its reading frames
    # faster than you process them, so by the time you process a frame, its an old frame
    class FreshFrameReader:
        def __init__(self, url):
            self.cap = cv2.VideoCapture(url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Limit internal buffer
            self.ret = False
            self.frame = None
            self.stopped = False
            threading.Thread(target=self.update, daemon=True).start()

        def update(self):
            while not self.stopped:
                if self.cap.grab():
                    self.ret, self.frame = self.cap.retrieve()

        def get_frame(self):
            return self.ret, self.frame

    # Configuration (edit this)
    width, height = 640, 480 # for logitech brio 100 i think
    fps = 30

    # model.export(format="ncnn",half=True,device='cpu') only call this once

    # List of FFmpeg low-latency flags
    command = [
        'ffmpeg',
        '-y',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f"{width}x{height}",
        '-r', str(fps), #rate set frame rate
        '-i', '-',
        '-c:v', 'libx264', #encoder
        '-preset', 'ultrafast', #setting for encoder
        '-tune', 'zerolatency', #livestream setting for encoder
        '-b:v', '5000',
        '-crf', '28',           #quality 0-63
        '-pix_fmt', 'yuv420p',
        '-f', 'rtsp',
        '-rtsp_transport', 'tcp',
        '-vf','fps=30',
        rtsp_out
    ]

    process = subprocess.Popen(command, stdin=subprocess.PIPE)

    # start the other threads
    reader = FreshFrameReader(rtsp_in)
    xygrabber = Getxy(UDP_IP,UDP_PORT)

    # main thread
    try:
        while True:
            ret, frame = reader.get_frame()
            if not ret or frame is None:
                continue
            result = model(frame, verbose=False, imgsz=(256,320)) # edit this, dependent on ncnn model you use, if want change need to export ncnn again
            annotated_frame = result[0].plot()
            annotated_frame = cv2.resize(annotated_frame,(width,height))
            # Stream out the latest result
            process.stdin.write(annotated_frame.tobytes())
            xy = xygrabber.get_xy_values()
            boxes = result[0].boxes
            if (xy is None) or (boxes.xyxy.numel() == 0):
                pass
            else:
                print("I've got",xy)
                sorted_boxes = sorted(boxes, key=lambda x:((x.xyxy[0][3]-x.xyxy[0][1])*(x.xyxy[0][2]-x.xyxy[0][0])))
                actual_box = []
                for box in sorted_boxes:
                    if (box.xyxy[0][0] < xy[0] < box.xyxy[0][2]) and (box.xyxy[0][1] < xy[1] < box.xyxy[0][3]):
                        temp = box.xyxy.numpy()
                        actual_box.append(int(temp[0][0]))
                        actual_box.append(int(temp[0][1]))
                        actual_box.append(int(temp[0][2]-temp[0][0]))
                        actual_box.append(int(temp[0][3]-temp[0][1]))
                        print("starting tracking")
                        print("bbox", actual_box)
                        await tracking_stuff.startTrackingDrone(frame,actual_box,reader,process,drone,trackHeight,moveForward)
                        break

    except KeyboardInterrupt:
        reader.stopped = True
        process.stdin.close()
        process.wait()
       

