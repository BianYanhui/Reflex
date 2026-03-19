#!/usr/bin/env python3

import os
import socket
import asyncio
import json
import struct
import subprocess
import time
from bpf import BPF

DEVICE_A_IP = "10.0.0.31"
DEVICE_B_IP = "10.0.0.32"
ROUTER_IP = "10.0.0.20"
CLIENT_IP = "10.0.0.10"

ROUTER_LISTEN_PORT = 8888
NACK_LISTEN_PORT = 9999

DEVICE_A_IP_INT = tuple(map(int, DEVICE_A_IP.split('.')))
DEVICE_A_IP_INT = DEVICE_A_IP_INT[0] << 24 | DEVICE_A_IP_INT[1] << 16 | DEVICE_A_IP_INT[2] << 8 | DEVICE_A_IP_INT[3]

DEVICE_B_IP_INT = tuple(map(int, DEVICE_B_IP.split('.')))
DEVICE_B_IP_INT = DEVICE_B_IP_INT[0] << 24 | DEVICE_B_IP_INT[1] << 16 | DEVICE_B_IP_INT[2] << 8 | DEVICE_B_IP_INT[3]

os.system("ip link set eth0 xdp obj /app/xdp_backpressure.o sec xdp 2>/dev/null || true")

try:
    bpf = BPF(src_file="/app/xdp_backpressure.c", cflags=["-Wno-compare-distinct-pointer-types"])
    fn = bpf.load_func("xdp_backpressure", BPF.XDP)
    bpf.attach_xdp(dev="eth0", fn=fn)
    print("[Router] eBPF XDP program loaded successfully on eth0")
except Exception as e:
    print(f"[Router] Note: eBPF loading via BCC failed: {e}")
    print("[Router] Falling back to userspace-only mode")
    bpf = None

penalty_set = set()

async def forward_to_device(data, target_ip, port=8888):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, (target_ip, port))
        sock.close()
        return True
    except Exception as e:
        print(f"[Router] Failed to forward to {target_ip}: {e}")
        return False

async def send_to_client(data, client_addr):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data, client_addr)
        sock.close()
    except Exception as e:
        print(f"[Router] Failed to send response to client: {e}")

async def check_penalty_map():
    global penalty_set
    try:
        if bpf is not None:
            penalty_map = bpf["penalty_map"]
            penalty_set = set()
            for key, value in penalty_map.items():
                penalty_set.add(key)
    except Exception as e:
        pass

async def handle_client_request(data, client_addr):
    task_data = json.loads(data.decode('utf-8'))
    task_id = task_data.get('task_id', 'unknown')
    
    await check_penalty_map()
    
    if DEVICE_A_IP_INT in penalty_set:
        print(f"[Router] [INFO] Device A penalized by eBPF. Rerouting to Device B...")
        target_ip = DEVICE_B_IP
    else:
        target_ip = DEVICE_A_IP
    
    print(f"[Router] Routed Task {task_id} to {target_ip}")
    
    success = await forward_to_device(data, target_ip)
    
    return target_ip, success

async def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('0.0.0.0', ROUTER_LISTEN_PORT))
    except OSError as e:
        print(f"[Router] Failed to bind to port {ROUTER_LISTEN_PORT}: {e}")
        return
    
    print(f"[Router] UDP Server listening on {ROUTER_IP}:{ROUTER_LISTEN_PORT}")
    
    loop = asyncio.get_event_loop()
    pending_forwards = {}
    
    while True:
        try:
            data, addr = await loop.sock_recvfrom(sock, 4096)
            
            if addr[0] == CLIENT_IP:
                target_ip, success = await handle_client_request(data, addr)
                if success:
                    task_data = json.loads(data.decode('utf-8'))
                    task_id = task_data.get('task_id')
                    pending_forwards[task_id] = (target_ip, addr)
            else:
                for task_id, (target_ip, client_addr) in list(pending_forwards.items()):
                    if data.decode('utf-8') == "Done":
                        print(f"[Router] Received result from {target_ip}, forwarding to client")
                        await send_to_client(data, client_addr)
                        del pending_forwards[task_id]
                        break
                        
        except Exception as e:
            print(f"[Router] Error: {e}")

async def nack_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('0.0.0.0', NACK_LISTEN_PORT))
    except OSError as e:
        print(f"[Router] Failed to bind NACK listener: {e}")
        return
    
    print(f"[Router] NACK listener on port {NACK_LISTEN_PORT}")
    
    loop = asyncio.get_event_loop()
    
    while True:
        try:
            data, addr = await loop.sock_recvfrom(sock, 4096)
            msg = data.decode('utf-8', errors='ignore')
            if msg == "OVERLOAD":
                print(f"[Router] [ALERT] NACK received from {addr[0]} - Device overloaded!")
                device_ip_int = tuple(map(int, addr[0].split('.')))
                device_ip_int = device_ip_int[0] << 24 | device_ip_int[1] << 16 | device_ip_int[2] << 8 | device_ip_int[3]
                penalty_set.add(device_ip_int)
                if bpf is not None:
                    try:
                        bpf["penalty_map"][device_ip_int] = 1
                    except:
                        pass
        except Exception as e:
            print(f"[Router] NACK listener error: {e}")

async def main():
    print("[Router] Starting Project Reflex Router...")
    print(f"[Router] OSPF State: Device_A (10.0.0.31) > Device_B (10.0.0.32)")
    
    await asyncio.gather(
        udp_server(),
        nack_listener()
    )

if __name__ == "__main__":
    asyncio.run(main())
