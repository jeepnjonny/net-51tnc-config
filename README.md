Amateur Radio · APRS · iGate

# NET-51TNC Config Tool

A cross-platform, browser-based configuration and monitoring tool for the NET-51TNC APRS iGate — no Windows required.

[jeepnjonny.github.io/net-51tnc-config](https://jeepnjonny.github.io/net-51tnc-config/) Single HTML file No install Python bridge required

## What it does

The NET-51TNC ships with a Windows-only configuration utility. This tool replicates that functionality as a single static HTML file that runs in any browser — Windows, Mac, Linux, or Raspberry Pi.

- Set callsign, SSID, server, passcode, beacon text, and all device parameters
- Configure serial ports, TTL/RS232 levels, weather board mode, and GPIO pins
- Adjust transmit audio level, squelch, PTT delay, and path options
- Configure digi aliases (WIDE1-1, WIDE2-2), filters, and UI-Flood settings
- Live stream of raw serial data — filter by callsign or text, hex view, record/pause

## How it works

The device runs a TCP server on port 60000. Browsers can't open raw TCP sockets, so a small local Python bridge sits in between.

```
Browser  index.html  ←── WebSocket ───→  bridge.py  ←── TCP :60000 ───→  NET-51TNC
```

The HTML tool connects to `ws://localhost:8765`; the bridge forwards everything to the device. Only one TCP client can connect at a time — the monitor tab shares the same connection as the config tabs.

## Quick start

1. Install the bridge

   ```
   pip install websockets
   ```

   One-time setup. Python 3.7+ required.
2. Start the bridge

   ```
   python bridge.py
   ```

   Listens on `ws://127.0.0.1:8765` by default. Pass `--host 0.0.0.0` to allow LAN access.
3. Open the tool

   Open `index.html` in your browser, or use the [hosted version](https://jeepnjonny.github.io/net-51tnc-config/). The hosted page still requires the bridge running locally.
4. Connect to your device

   Enter your device IP (default `192.168.0.120`) and port (`60000`), then click **Connect**. Recent IPs are remembered for quick access.

## Weather sensor support

The I/O 1 header (Pin 5) supports a dedicated weather board outputting TTL serial at 2400 baud in APRS format. Set JP1 on the 51TNC to TTL mode.

DWM-51WS3 "Three Generations APRS WS1 WS3" (AliExpress) — TTL serial output; internal RS485 is sensor-side only

ADS-WS1 Argent Data Systems — discontinued

### Wiring (screw terminal header)

| Pin | Signal | Connect to |
| --- | --- | --- |
| 1 | 5 V | Weather board VCC |
| 4 | GND | Weather board GND |
| 5 (I/O 1) | DATA | Weather board TX (TTL, 2400 baud) |

## Protocol notes

The device uses a newline-delimited plain ASCII protocol on port 60000. It responds with the current configuration on connect and echoes serial traffic in the monitor stream. Only one TCP client can be connected at a time — a second connection boots the first.
