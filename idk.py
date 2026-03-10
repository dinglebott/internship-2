from mavsdk import System
from mavsdk.offboard import VelocityBodyYawspeed
import asyncio
import math
import csrt_stuff
import cv2
import cv_function
import numpy as np
from ultralytics import YOLO
import tracking_stuff

# initialisation for cv
rtsp_out = "rtsp://127.0.0.1:8554/my_stream" 
rtsp_in = "rtsp://127.0.0.1:8554/usb_cam"
model = YOLO("train12_ncnn_model_FAST")


# OPTIONS
trackHeight = False
moveForward = False

# HELPER
def getDist(obj1, obj2):
    return math.sqrt((obj1["cx"] - obj2["cx"])**2 + (obj1["cy"] - obj2["cy"])**2)

# ACTIONS
async def forward(drone):
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(1, 0, 0, 0))
    await asyncio.sleep(2)
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))

async def backward(drone):
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(-1, 0, 0, 0))
    await asyncio.sleep(2)
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))

async def left(drone):
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, -1, 0, 0))
    await asyncio.sleep(2)
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))

async def right(drone):
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 1, 0, 0))
    await asyncio.sleep(2)
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))

async def up(drone):
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, -0.5, 0))
    await asyncio.sleep(1)
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))

async def down(drone):
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0.5, 0))
    await asyncio.sleep(1)
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))
'''
async def follow(drone):
    # start tracker
    cap, roi_hist, track_window, term_crit = camshift_tracker.initTracker()
    currentBox = screen = None
    # define success condition
    def reachedTarget():
        if currentBox and screen:
            if getDist(currentBox, screen) <= 100 and currentBox["height"] >= 0.8*screen["height"]:
                return True
            else:
                return False
        else:
            return False
    
    # following loop
    try:
        while True:
            if not reachedTarget():
                # reset parameters
                yaw = xvel = yvel = 0 # down is positive yvel
                # update target box and screen
                ret_val, frame, currentBox, screen = camshift_tracker.updateTracker(cap, roi_hist, track_window, term_crit)
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
                await drone.offboard.set_velocity_body(VelocityBodyYawspeed(xvel, 0, yvel, yaw))
                await asyncio.sleep(0.1)
                # update gui
                pts = cv2.boxPoints(ret_val)
                pts = np.intp(pts)
                result = cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
                cv2.imshow("Tracking", result)
                cv2.waitKey(1)
            else:
                break
    # cancelled by STOP/X command
    except asyncio.CancelledError:
        print("Follow mode stopped")
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))
        raise # mark async task as cancelled - error caught again in main()
    else:
        print("Target reached")
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))
'''
async def cv(drone):
    # start tracker
    bbox = cv_function.cv_stuff()
    cap, frame = csrt_stuff.getBox()
    # create CSRT tracker
    tracker = cv2.TrackerCSRT_create()
    # initialize tracker
    tracker.init(frame, bbox)
    currentBox = screen = None
    # define success condition
    def reachedTarget():
        if currentBox and screen:
            if getDist(currentBox, screen) <= 100 and currentBox["height"] >= 0.8*screen["height"]:
                return True
            else:
                return False
        else:
            return False
    
    # following loop
    try:
        while True:
            if not reachedTarget():
                # reset parameters
                yaw = xvel = yvel = 0 # down is positive yvel
                # update target box and screen
                # get new frame, update
                ret, frame = cap.read()
                if not ret:
                    break
                success, bbox = tracker.update(frame)
                # display
                if success:
                    x, y, w, h = [int(v) for v in bbox]
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "Tracking failure", (50, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

                cv2.imshow("CSRT Tracking", frame) # change to rtsp output

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                currentBox = bbox
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
                await drone.offboard.set_velocity_body(VelocityBodyYawspeed(xvel, 0, yvel, yaw))
                await asyncio.sleep(0.1)
            else:
                break
    # cancelled by STOP/X command
    except asyncio.CancelledError:
        print("Follow mode stopped")
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))
        raise # mark async task as cancelled - error caught again in main()
    else:
        print("Target reached")
        await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))  

# tracking_stuff.startTrackingDrone



# MAIN
async def main():
    drone = System()
    print("Before connect called")
    await drone.connect(system_address="udpin://0.0.0.0:14540")
    print("After connect called")

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Drone connected")
            break
        else:
            print("Drone doesn't connect")

    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_local_position_ok and health.is_home_position_ok:
            print("Drone position OK")
            break
    
    async for health in drone.telemetry.health():
        if health.is_armable:
            print("Drone ready to arm")
            break

    await drone.action.arm()
    print("Drone armed")
    await drone.action.takeoff()
    print("Taking off...")
    await asyncio.sleep(10)
    print("Drone flying")
    await drone.offboard.set_velocity_body(VelocityBodyYawspeed(0, 0, 0, 0))
    await drone.offboard.start()
    print("Offboard mode activated")
    global trackHeight, moveForward
    r1 = input("Adjust altitude? Y/N")
    r2 = input("Move towards target? Y/N")
    if r1.upper() == "Y":
        trackHeight = True
    if r2.upper() == "Y":
        moveForward = True

    # command loop
    followTask = None
    while True:
        # take new commands
        cmd = await asyncio.get_event_loop().run_in_executor(None, input, "Input command (W/A/S/D/C/V/F/STOP/X):")
        
        # respond to command
        if cmd.upper() == "X": # land
            if followTask and not followTask.done():
                followTask.cancel()
                try:
                    await followTask # catch CancelledError raised from follow()
                except asyncio.CancelledError:
                    pass
            # land drone
            await drone.offboard.stop()
            await drone.action.land()
            print("Drone landing...")
            # wait for drone to disarm
            async for isArmed in drone.telemetry.armed():
                if not isArmed:
                    print("Drone disarmed")
                    break
            break
        
       # elif cmd.upper() == "F": # follow
       #     if followTask is None or followTask.done():
       #         followTask = asyncio.create_task(follow(drone))
       #         print("Follow mode started")

        elif cmd.upper() == "C":
            if followTask is None or followTask.done():
                followTask = asyncio.create_task(cv_function.cv_stuff(model, rtsp_in,rtsp_out,drone))
                print("CV mode started")       
        
        elif cmd.upper() == "STOP": # stop follow
            if followTask and not followTask.done():
                followTask.cancel()
                try:
                    await followTask # catch CancelledError raised from follow()
                except asyncio.CancelledError:
                    pass
        
        elif cmd.upper() == "W": # forward
            if followTask is None or followTask.done():
                await forward(drone)
        
        elif cmd.upper() == "A": # left
            if followTask is None or followTask.done():
                await left(drone)
        
        elif cmd.upper() == "S": # back
            if followTask is None or followTask.done():
                await backward(drone)
        
        elif cmd.upper() == "D": # right
            if followTask is None or followTask.done():
                await right(drone)
        
        elif cmd.upper() == "C": # up
            if followTask is None or followTask.done():
                await up(drone)
        
        elif cmd.upper() == "V": # down
            if followTask is None or followTask.done():
                await down(drone)

asyncio.run(main())