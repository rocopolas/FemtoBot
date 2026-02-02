import httpx
import asyncio

async def list_models():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                print("Available models:")
                for m in models:
                    print(f"- {m['name']}")
            else:
                print(f"Error accessing Ollama: Status {response.status_code}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
