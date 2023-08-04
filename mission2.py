#!/usr/bin/env python3
import asyncio
import random
import math

from mavsdk import System
# from mavsdk.offboard import (OffboardError, VelocityBodyYawspeed)
from mavsdk.offboard import (OffboardError, PositionNedYaw)

CRASHING_THRESHOLD = 0
RETURN_TO_BASE_THRESHOLD = 10
UTIL_THRESHOLD = 50
t_elapsed = 0
t_max = 300
t_sleep = 15
net_wait = 10

def util_fcn(d):
    for key in d:
        U_safe, U_mission, U_time = key
        d[key] = 0.4 * U_safe + 0.3 * U_mission + 0.3 * U_time
    return d

async def degrade(waypoints_completed, num_waypoints, battery):
    print("current waypoints: ", waypoints_arr[waypoints_completed])
    while waypoints_completed <= num_waypoints-1:
        if battery <= CRASHING_THRESHOLD:
                mission = 0
                print("DRONE HAS CRASHED")
                return -1
        if 66 < battery <= 70:
                #cut off last waypoint
                print("CUTTING OFF LAST WAYPOINT")
                waypoints_arr = waypoints_arr[:-1]
                num_waypoints -= 1
        if 21 < battery <= 30:
                #cut off last two waypoints
                print("CUTTING OFF LAST 2 WAYPOINTS")
                waypoints_arr = waypoints_arr[:-2]
                num_waypoints -= 2
                completed = waypoints_completed
        if battery <= RETURN_TO_BASE_THRESHOLD:
                safety = 1
                return -1
        await drone.offboard.set_position_ned(
            waypoints_arr[waypoints_completed])
        await asyncio.sleep(5)
        battery -= 10
        waypoints_completed += 1

# async def timer():
#     global t_elapsed
#     while True:
#         t_elapsed += 1
#         await asyncio.sleep(1)

# environmental model for how much battery is taken up to go to each waypoint
async def run():
    global t_elapsed
    num_waypoints = 18
    battery = 100
    waypoints_completed = 0
    already_failed = False
    # util_fcn = 0.8 * safety + 0.2 * completed

    # waypoints_arr = set_waypoints(num_waypoints)

    safety = 1 #Safety = 0 means no home, 1 = is home
    completed = waypoints_completed / num_waypoints

    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"-- Connected to drone!")
            break

    print("Waiting for drone to have a global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position estimate OK")
            break

    print("-- Arming")
    await drone.action.arm()
    
    print("-- Setting initial setpoint")
    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, 0.0, 0.0))

    print("-- Starting offboard")
    try:
        await drone.offboard.start()
    except OffboardError as error:
        print(f"Starting offboard mode failed with error code: \
              {error._result.result}")
        print("-- Disarming")
        await drone.action.disarm()
        return

    # square thingy
    waypoints_arr = [PositionNedYaw(0.0, 0.0, -15.0, 0.0), 
    PositionNedYaw(25.0, 0.0, -15.0, 0.0),
    PositionNedYaw(0.0, 25.0, -15.0, 0.0), PositionNedYaw(-25.0, 0.0, -15.0, 0.0), 
    PositionNedYaw(0.0, -25.0, -15.0, 0.0),
    PositionNedYaw(50.0, 0.0, -15.0, 0.0),
    PositionNedYaw(0.0, 50.0, -15.0, 0.0), PositionNedYaw(-50.0, 0.0, -15.0, 0.0), 
    PositionNedYaw(0.0, -50.0, -15.0, 0.0),
    PositionNedYaw(75.0, 0.0, -15.0, 0.0),
    PositionNedYaw(0.0, 75.0, -15.0, 0.0), PositionNedYaw(-75.0, 0.0, -15.0, 0.0), 
    PositionNedYaw(0.0, -75.0, -15.0, 0.0),
    PositionNedYaw(100.0, 0.0, -15.0, 0.0),
    PositionNedYaw(0.0, 100.0, -15.0, 0.0), PositionNedYaw(-100.0, 0.0, -15.0, 0.0), 
    PositionNedYaw(0.0, -100.0, -15.0, 0.0),
    PositionNedYaw(0.0,0.0,0.0,0.0)] 

    
    while waypoints_completed <= num_waypoints-1:
        print("current waypoint: ", waypoints_arr[waypoints_completed])
        util = False
        if not already_failed:
            if random.random() < 0.2:
                print("DELAY")
                util = True
                already_failed = True
        else:
            util = False
        if util:
            print("USING UTIL FCN")
            print("elapsed:", t_elapsed)
            trace_1 = (1, 1, ((t_max - t_elapsed) - net_wait + math.floor((t_max - t_elapsed - net_wait) / t_sleep)) / t_max)
            trace_2 = (0, 0.8, ((t_max - t_elapsed) + math.floor((t_max - t_elapsed) / t_sleep)) / t_max)  # Need environmental model to know how much further you can go on decreased speed
            trace_3 = (0, waypoints_completed / num_waypoints, ((t_max - t_elapsed) + math.floor((t_max - t_elapsed) / t_sleep)) / t_max)
            rec_traces = {trace_1: 0, trace_2: 0, trace_3: 0}
            ranked_traces = util_fcn(rec_traces)
            best_trace = max(ranked_traces, key=lambda k: ranked_traces[k])
            print("best_trace", best_trace)
            if best_trace == trace_1:
                print("WAITING")
                await asyncio.sleep(net_wait)
                t_elapsed += net_wait
            elif best_trace == trace_2:
                val = degrade(waypoints_completed, num_waypoints, battery)
                if val == -1:
                    break
            else:
                break
        # timer_task = asyncio.create_task(timer())
        await drone.offboard.set_position_ned(
            waypoints_arr[waypoints_completed])
        await asyncio.sleep(t_sleep)
        t_elapsed += t_sleep
        battery -= 10
        waypoints_completed += 1
    # timer_task.cancel()
    print(t_elapsed)
    print("-- Landing")
    await drone.action.land()

    print("-- Stopping offboard")
    try:
        await drone.offboard.stop()
    except OffboardError as error:
        print(f"Stopping offboard mode failed with error code: \
              {error._result.result}")
    
# def set_waypoints(num_waypoints):
#         waypoints_arr = []
#         for i in range(num_waypoints):
#                     position = VelocityBodyYawspeed((2)^i, i,  -2-i, 0)
#                     waypoints_arr.append(position)
#         return waypoints_arr

if __name__ == "__main__":
    # Run the asyncio loop
    asyncio.run(run())
