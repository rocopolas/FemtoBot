import httpx
import asyncio

async def check_raw_output():
    model = "glm-4.7-flash:q8_0"
    print(f"Checking raw output from model: {model}...")
    
    messages = [{"role": "user", "content": "Explain briefly why the sky is blue. Show your thinking process."}]
    payload = {"model": model, "messages": messages, "stream": False}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://localhost:11434/api/chat", json=payload, timeout=60.0)
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                print("\n--- RAW CONTENT START ---")
                print(content)
                print("--- RAW CONTENT END ---\n")
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(check_raw_output())
