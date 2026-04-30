#!/usr/bin/env python3
import asyncio
import websockets
import json
import sys

AMP_ADDRESS = "ws://192.168.16.221:1234"

ENDPOINTS_TO_TRY = [
    "/amp",
    "/amp/deviceInfo",
    "/amp/power",
    "/amp/powerSupply",
    "/amp/status",
    "/amp/acMains",
    "/amp/acPower",
    "/amp/powerStatus",
    "/amp/systemStatus",
    "/amp/system",
    "/amp/info",
    "/amp/diagnostics",
    "/amp/thermal",
    "/amp/metrics",
]

async def test_endpoint(ws, url, msg_id):
    message = {
        "leaApi": "1.0",
        "url": url,
        "method": "get",
        "id": msg_id
    }

    await ws.send(json.dumps(message))

    try:
        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
        data = json.loads(response)
        return data
    except asyncio.TimeoutError:
        return {"timeout": True, "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}

async def main():
    addr = sys.argv[1] if len(sys.argv) > 1 else AMP_ADDRESS

    print(f"Connecting to {addr}...")

    try:
        async with websockets.connect(addr) as ws:
            print(f"Connected!\n")
            print("=" * 60)

            for i, endpoint in enumerate(ENDPOINTS_TO_TRY, start=1):
                print(f"\nTrying: {endpoint}")
                print("-" * 40)

                result = await test_endpoint(ws, endpoint, i)

                if "error" in result and isinstance(result.get("error"), dict):
                    print(f"  ERROR: {result['error']}")
                elif "timeout" in result:
                    print(f"  TIMEOUT (no response)")
                elif "result" in result:
                    print(f"  SUCCESS!")
                    print(f"  Response: {json.dumps(result['result'], indent=4)}")
                else:
                    print(f"  Response: {json.dumps(result, indent=4)}")

                await asyncio.sleep(0.2)

            print("\n" + "=" * 60)
            print("Discovery complete!")

    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
