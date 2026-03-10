import cv2
import math
from mavsdk.offboard import VelocityBodyYawspeed
import asyncio


# HELPER
def getDist(obj1, obj2):
    return math.sqrt((obj1["cx"] - obj2["cx"])**2 + (obj1["cy"] - obj2["cy"])**2)

async def startTrackingDrone(frame,bbox,reader,process,drone,trackHeight,moveForward):
    currentBox = screen = None
    def reachedTarget():
        if currentBox and screen:
            if getDist(currentBox, screen) <= 100 and currentBox["height"] >= 0.8*screen["height"]:
                return True
            else:
                return False
        else:
            return False

    tracker = cv2.TrackerCSRT_create()
    tracker.init(frame, bbox)
    while True:
        ret, frame = reader.get_frame()
        if not ret:
            break
        success, bbox = tracker.update(frame)
        if success:
            x, y, w, h = [int(v) for v in bbox]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        else:
            return None  
        process.stdin.write(frame.tobytes())

        if reachedTarget():
            print("I've reached")

        if not reachedTarget():
            # get new frame, update
            yaw = xvel = yvel = 0 # down is positive yvel
            currentBox = {
                "cx": bbox[0]+bbox[2]/2,
                "cy": bbox[1]+bbox[3]/2,
                "width": bbox[2],
                "height": bbox[3],
                "angle": 0
            }
            frameHeight, frameWidth = frame.shape[:2]
            screen = {
                "cx": frameWidth / 2,
                "cy": frameHeight / 2,
                "width": frameWidth,
                "height": frameHeight
            }

            if currentBox is None or screen is None:
                await asyncio.sleep(0.1)
                continue
            # correct drone direction
            if currentBox["cx"] < screen["cx"] - 20:
                yaw = -25
            elif currentBox["cx"] > screen["cx"] + 20:
                yaw = 25
            # correct drone elevation
            if trackHeight:
                if currentBox["cy"] < screen["cy"] - 20:
                    yvel = -0.5
                elif currentBox["cy"] > screen["cy"] + 20:
                    yvel = 0.5
            # move drone forward if target is roughly in front
            if moveForward and getDist(currentBox, screen) <= 150:
                xvel = 0.8
            # command drone
            print("moving drone")
            print(xvel,yvel,yaw)
            await drone.offboard.set_velocity_body(VelocityBodyYawspeed(xvel, 0, yvel, yaw))
            await asyncio.sleep(0.1)