import httpx
import asyncio
import sys

async def list_models():
    print("Starting check...", flush=True)
    try:
        async with httpx.AsyncClient() as client:
            print("Sending request...", flush=True)
            response = await client.get("http://localhost:11434/api/tags")
            print(f"Status Code: {response.status_code}", flush=True)
            print(f"Raw Response: {response.text}", flush=True)
    except Exception as e:
        print(f"EXCEPTION: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(list_models())
