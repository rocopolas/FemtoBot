import httpx
import json
from typing import AsyncGenerator

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def stream_chat(self, model: str, messages: list) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True 
        }
        
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", url, json=payload, timeout=None) as response:
                    if response.status_code != 200:
                        error_detail = ""
                        try:
                            # Try to read the error message from the response
                            async for chunk in response.aiter_text():
                                error_detail += chunk
                        except:
                            pass
                        yield f"Error: Ollama returned status {response.status_code}. Details: {error_detail}"
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                yield data["message"].get("content", "")
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            except httpx.ConnectError:
                yield "Error: No se pudo conectar a Ollama. Asegúrate de que 'ollama serve' esté corriendo."
            except httpx.RemoteProtocolError:
                yield "Error: La conexión con Ollama se cerró inesperadamente. (Posible crash del modelo o timeout)."
            except Exception as e:
                yield f"Error: {str(e)}"

    async def unload_model(self, model: str):
        """Unloads the model from memory by sending keep_alive: 0"""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "keep_alive": 0
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url, json=payload)
        except:
            pass # Best effort cleanup

    async def describe_image(self, model: str, image_base64: str, prompt: str = "Describe esta imagen en detalle.") -> str:
        """Uses a vision model to describe an image."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64]
                }
            ],
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=120.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "[Sin descripción]")
                else:
                    return f"[Error del modelo de visión: {response.status_code}]"
        except httpx.ConnectError:
            return "[Error: No se pudo conectar a Ollama]"
        except Exception as e:
            return f"[Error: {str(e)}]"
