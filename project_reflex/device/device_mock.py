import os
import socket
import asyncio
import json
import struct
import sys

DEVICE_NAME = os.getenv("DEVICE_NAME", "Device_A")
DEVICE_IP = os.getenv("DEVICE_IP", "10.0.0.31")
THRESHOLD = int(os.getenv("THRESHOLD", "5"))
ROUTER_IP = "10.0.0.20"
ROUTER_NACK_PORT = 9999
SERVER_PORT = 8888

active_tasks = 0
lock = asyncio.Lock()

async def send_nack():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b"OVERLOAD", (ROUTER_IP, ROUTER_NACK_PORT))
        sock.close()
        print(f"[{DEVICE_NAME}] NACK sent to Router at {ROUTER_IP}:{ROUTER_NACK_PORT}")
    except Exception as e:
        print(f"[{DEVICE_NAME}] Failed to send NACK: {e}")

async def handle_task(data, addr):
    global active_tasks
    
    async with lock:
        active_tasks += 1
        current_count = active_tasks
    
    print(f"[{DEVICE_NAME}] Task received. Active: {current_count}/{THRESHOLD}")
    
    if current_count > THRESHOLD:
        print(f"[{DEVICE_NAME}] [CRITICAL] VRAM OOM Warning! Sending NACK...")
        await send_nack()
        async with lock:
            active_tasks -= 1
        return None
    
    await asyncio.sleep(0.5)
    
    async with lock:
        active_tasks -= 1
    
    return "Done"

async def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('0.0.0.0', SERVER_PORT))
    except OSError as e:
        print(f"[{DEVICE_NAME}] Failed to bind to port {SERVER_PORT}: {e}")
        sys.exit(1)
    
    print(f"[{DEVICE_NAME}] UDP Server listening on {DEVICE_IP}:{SERVER_PORT}")
    
    loop = asyncio.get_event_loop()
    
    while True:
        try:
            data, addr = await loop.sock_recvfrom(sock, 4096)
            task_data = json.loads(data.decode('utf-8'))
            task_id = task_data.get('task_id', 'unknown')
            
            result = await handle_task(data, addr)
            
            if result:
                await loop.sock_sendto(sock, result.encode('utf-8'), addr)
                print(f"[{DEVICE_NAME}] Task {task_id} completed, result sent")
        except Exception as e:
            print(f"[{DEVICE_NAME}] Error handling task: {e}")

async def main():
    print(f"[{DEVICE_NAME}] Starting with threshold={THRESHOLD}")
    await udp_server()

if __name__ == "__main__":
    asyncio.run(main())
