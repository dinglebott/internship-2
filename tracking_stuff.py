import cv2
import numpy as np
import math
from mavsdk import System
from mavsdk.offboard import VelocityBodyYawspeed
import asyncio


# HELPER
def getDist(obj1, obj2):
    return math.sqrt((obj1["cx"] - obj2["cx"])**2 + (obj1["cy"] - obj2["cy"])**2)

# OPTIONS
trackHeight = False
moveForward = False

def initTracker(bbox, frame):
    x, y, w, h = bbox
    track_window = (x, y, w, h)
    # convert ROI to HSV
    roi = frame[y:y+h, x:x+w]
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # filter low light pixels
    mask = cv2.inRange(
        hsv_roi,
        np.array((0., 60., 32.)),
        np.array((180., 255., 255.))
    )
    # compute and normalise histogram
    roi_hist = cv2.calcHist([hsv_roi], [0], mask, [180], [0, 180])
    cv2.normalize(roi_hist, roi_hist, 0, 255, cv2.NORM_MINMAX)
    # termination criteria
    term_crit = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
        10,
        1
    )
    return roi_hist, track_window, term_crit

def updateTracker(frame, roi_hist, track_window, term_crit):
    # backproject histogram
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    dst = cv2.calcBackProject([hsv], [0], roi_hist, [0, 180], 1)
    # magic algo
    ret_val, track_window = cv2.CamShift(dst, track_window, term_crit)
    # unpack target box and screen info
    (cx, cy), (width, height), angle = ret_val
    currentBox = {
        "cx": cx,
        "cy": cy,
        "width": width,
        "height": height,
        "angle": angle
    }
    frameHeight, frameWidth = frame.shape[:2]
    screen = {
        "cx": frameWidth / 2,
        "cy": frameHeight / 2,
        "width": frameWidth,
        "height": frameHeight
    }
    return ret_val, frame, currentBox, screen

def startTracking(frame, bbox,reader,process):
    # create CSRT tracker
    tracker = cv2.TrackerCSRT_create()
    # initialize tracker
    tracker.init(frame, bbox)

    while True:
        # get new frame, update
        ret, frame = reader.get_frame()
        if not ret:
            break
        success, bbox = tracker.update(frame)
        # display
        if success:
            x, y, w, h = [int(v) for v in bbox]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        else:
            return None
        process.stdin.write(frame.tobytes())

async def startTrackingDrone(frame,bbox,reader,process,drone):
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










'''
def init_CSRT_Tracker(frame,bbox):
    # create CSRT tracker
    tracker = cv2.TrackerCSRT_create()
    # initialize tracker
    tracker.init(frame, bbox)
    return tracker

def startTracking(frame, bbox,reader,tracker):

    # get new frame, update
    ret, frame = reader.get_frame()
    if not ret:
        pass
    success, bbox = tracker.update(frame)
    # display
    if success:
        x, y, w, h = [int(v) for v in bbox]
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Tracking failure", (50, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

    return frame

    #cap.release()
    #cv2.destroyAllWindows()
    '''