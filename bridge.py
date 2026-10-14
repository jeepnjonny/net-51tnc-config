#!/usr/bin/env python3
"""
bridge.py — WebSocket → TCP bridge for 51TNC Config App
========================================================

Each WebSocket client connection gets a dedicated TCP connection to the TNC device.

PROTOCOL:
  1. HTML app connects to this bridge via WebSocket
  2. First message from app must be "IP:PORT" (e.g. "192.168.0.120:60000")
  3. Bridge opens TCP connection to that IP:PORT
  4. All subsequent binary/text frames are forwarded bidirectionally

USAGE:
  pip install websockets
  python3 bridge.py [--host HOST] [--port PORT]

  HOST : bind address for WebSocket server (default: localhost)
  PORT : WebSocket port (default: 8765)

  Then open index.html and set Bridge URL to ws://localhost:8765
"""

import asyncio
import socket
import sys
import argparse

try:
    import websockets
    import websockets.server
except ImportError:
    print("ERROR: 'websockets' package not found.")
    print("Install it with:  pip install websockets")
    sys.exit(1)


BRIDGE_HOST = "localhost"
BRIDGE_PORT = 8765
TCP_TIMEOUT  = 10          # seconds to establish TCP connection
CHUNK_SIZE   = 4096


async def handle_client(websocket):
    """Bridge one WebSocket client to one TNC TCP connection."""
    remote = websocket.remote_address
    print(f"[WS ] Client connected from {remote}")

    # ---- Step 1: receive target address ----
    try:
        first_msg = await asyncio.wait_for(websocket.recv(), timeout=10)
    except asyncio.TimeoutError:
        print(f"[WS ] {remote}: timeout waiting for target address — disconnecting")
        return

    if isinstance(first_msg, bytes):
        first_msg = first_msg.decode("utf-8", errors="replace")
    first_msg = first_msg.strip()

    try:
        if ":" not in first_msg:
            raise ValueError("expected IP:PORT")
        host, port_str = first_msg.rsplit(":", 1)
        port = int(port_str)
    except (ValueError, IndexError) as e:
        print(f"[WS ] {remote}: bad target address '{first_msg}': {e}")
        await websocket.close(1008, "Expected first message: IP:PORT")
        return

    print(f"[TCP] Connecting to {host}:{port} …")

    # ---- Step 2: open TCP connection ----
    loop = asyncio.get_event_loop()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=TCP_TIMEOUT
        )
    except asyncio.TimeoutError:
        print(f"[TCP] Timeout connecting to {host}:{port}")
        await websocket.close(1011, f"TCP connect timeout to {host}:{port}")
        return
    except OSError as e:
        print(f"[TCP] Connection failed: {e}")
        await websocket.close(1011, f"TCP connect failed: {e}")
        return

    print(f"[TCP] Connected to {host}:{port}")

    # ---- Step 3: bidirectional relay ----
    tcp_closed = asyncio.Event()

    async def tcp_to_ws():
        """Read from TCP, write to WebSocket."""
        try:
            while True:
                data = await asyncio.wait_for(reader.read(CHUNK_SIZE), timeout=30)
                if not data:
                    print(f"[TCP] Remote closed connection")
                    break
                print(f"[TCP→WS] {len(data)} bytes")
                await websocket.send(data)
        except asyncio.TimeoutError:
            print(f"[TCP] Read timeout")
        except Exception as e:
            print(f"[TCP→WS] Error: {e}")
        finally:
            tcp_closed.set()

    async def ws_to_tcp():
        """Read from WebSocket, write to TCP."""
        try:
            async for msg in websocket:
                data = msg if isinstance(msg, bytes) else msg.encode("utf-8")
                print(f"[WS→TCP] {len(data)} bytes  hex={data[:16].hex()}")
                writer.write(data)
                await writer.drain()
        except Exception as e:
            print(f"[WS→TCP] Error: {e}")
        finally:
            tcp_closed.set()

    try:
        await asyncio.gather(tcp_to_ws(), ws_to_tcp())
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        print(f"[WS ] Client {remote} disconnected")


async def main(host, port):
    print(f"51TNC WebSocket Bridge")
    print(f"Listening on ws://{host}:{port}")
    print(f"Point your browser app's Bridge URL to ws://{host}:{port}")
    print(f"Press Ctrl+C to stop\n")

    async with websockets.server.serve(handle_client, host, port):
        await asyncio.Future()   # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebSocket→TCP bridge for 51TNC Config App")
    parser.add_argument("--host", default=BRIDGE_HOST, help=f"Bind host (default: {BRIDGE_HOST})")
    parser.add_argument("--port", default=BRIDGE_PORT, type=int, help=f"WebSocket port (default: {BRIDGE_PORT})")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        print("\nBridge stopped.")
