#!/usr/bin/env python3

import asyncio
import socket
import json
import time

ROUTER_IP = "10.0.0.20"
ROUTER_PORT = 8888
TOTAL_REQUESTS = 15
TIME_WINDOW_MS = 100

results = []

async def send_request(task_id, results_list):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    send_time = time.time()
    task_data = {
        "task_id": task_id,
        "intent": "LLM_Inference"
    }
    data = json.dumps(task_data).encode('utf-8')
    
    sock.sendto(data, (ROUTER_IP, ROUTER_PORT))
    
    print(f"[Client] Task {task_id} sent at {send_time:.6f}")
    
    try:
        sock.settimeout(10.0)
        response, addr = sock.recvfrom(4096)
        recv_time = time.time()
        results_list.append({
            "task_id": task_id,
            "send_time": send_time,
            "recv_time": recv_time,
            "latency_ms": (recv_time - send_time) * 1000
        })
        print(f"[Client] Task {task_id} received response at {recv_time:.6f}, latency: {(recv_time - send_time)*1000:.2f}ms")
    except socket.timeout:
        print(f"[Client] Task {task_id} timed out")
        results_list.append({
            "task_id": task_id,
            "send_time": send_time,
            "recv_time": None,
            "latency_ms": None
        })
    finally:
        sock.close()

async def micro_burst():
    print(f"[Client] Starting micro-burst: {TOTAL_REQUESTS} requests in {TIME_WINDOW_MS}ms")
    print(f"[Client] Target: {ROUTER_IP}:{ROUTER_PORT}")
    
    start_time = time.time()
    
    tasks = []
    for i in range(1, TOTAL_REQUESTS + 1):
        task = send_request(i, results)
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    print(f"\n[Client] All requests completed in {elapsed*1000:.2f}ms")
    
    successful = sum(1 for r in results if r["latency_ms"] is not None)
    print(f"[Client] Success rate: {successful}/{TOTAL_REQUESTS}")
    
    if successful > 0:
        avg_latency = sum(r["latency_ms"] for r in results if r["latency_ms"] is not None) / successful
        print(f"[Client] Average latency: {avg_latency:.2f}ms")

if __name__ == "__main__":
    asyncio.run(micro_burst())
