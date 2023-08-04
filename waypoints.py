#!/usr/bin/env python3
import asyncio

from mavsdk import System
from mavsdk.offboard import (OffboardError, PositionNedYaw)

CRASHING_THRESHOLD = 0
RETURN_TO_BASE_THRESHOLD = 20

async def run():
    """ Does Offboard control using position NED coordinates. """
    battery = 100
    prev_idx= 0
    waypoints_completed = 0
    num_waypoints = 5

    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"-- Connected to drone!")
            breakd

    print("Waiting for drone to have a global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position estimate OK")
            break

    print("-- Arming")
    await drone.action.arm()

    print("-- Taking off")
    await drone.action.takeoff()

    await asyncio.sleep(10)

    print("-- Setting initial setpoint")
    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, 0.0, 0.0))

    print("-- Starting offboard")
    try:
        await drone.offboard.start()
    except OffboardError as error:
        print(f"Starting offboard mode failed \
                with error code: {error._result.result}")
        print("-- Disarming")
        await drone.action.disarm()
        return
   
    waypoints_arr = set_waypoints(num_waypoints)
    while True:
        print("completed: ", waypoints_completed)
        if battery <= CRASHING_THRESHOLD:
                print("DRONE HAS CRASHED")
                break
        if 50 < battery <= 70:  
                #cut off last waypoint
                waypoints_arr = waypoints_arr[:-1]
        if 30 < battery <= 50:
                #cut off last two waypoints
                waypoints_arr = waypoints_arr[:-2]
        if battery <= RETURN_TO_BASE_THRESHOLD:
                print("-- Landing")
                await drone.action.land()
                break
        #await waypoints(waypoints_completed, waypoints_arr)
        #waypoints(waypoints_completed, waypoints_arr)
        print("current waypoints: ", waypoints_arr[waypoints_completed])
        await drone.offboard.set_position_ned(
        waypoints_arr[waypoints_completed])
        await asyncio.sleep(10)
        battery -= 10
        waypoints_completed += 1

def set_waypoints(num_waypoints):
        waypoints_arr = []
        for i in range(1, num_waypoints):
                for j in range(1,10):
                        position = PositionNedYaw(j+5,j+3,0,j+1)
                        waypoints_arr.append(position)
        return waypoints_arr

if __name__ == "__main__":
    # Run the asyncio loop
    asyncio.run(run())
