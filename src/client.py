"""LLM API client for FemtoBot with streaming support.

Supports two backends:
  - ollama: Ollama native API (default)
  - lmstudio: LM Studio OpenAI-compatible API
"""
import httpx
import json
import logging
import re
from typing import AsyncGenerator, Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Type aliases
Message = Dict[str, Any]
Messages = List[Message]


def _get_backend_config() -> Dict[str, Any]:
    """Read backend config from config.yaml (lazy import to avoid circular deps)."""
    try:
        from utils.config_loader import get_config
        backend = get_config("BACKEND") or {}
        if not isinstance(backend, dict):
            backend = {}
        return {
            "provider": backend.get("PROVIDER", "ollama").lower(),
            "ollama_url": backend.get("OLLAMA_URL", "http://localhost:11434"),
            "lmstudio_url": backend.get("LMSTUDIO_URL", "http://localhost:1234"),
        }
    except Exception:
        return {
            "provider": "ollama",
            "ollama_url": "http://localhost:11434",
            "lmstudio_url": "http://localhost:1234",
        }


class OllamaClient:
    """
    Client for interacting with Ollama or LM Studio API.
    
    Uses a single persistent httpx.AsyncClient to avoid
    creating a new TCP connection on every request.
    """
    
    _shared_client: Optional[httpx.AsyncClient] = None
    
    def __init__(self, base_url: str = None, provider: str = None) -> None:
        """
        Initialize LLM client.
        
        Args:
            base_url: Override base URL (if None, read from config)
            provider: "ollama" or "lmstudio" (if None, read from config)
        """
        cfg = _get_backend_config()
        self.provider = (provider or cfg["provider"]).lower()
        
        if base_url:
            self.base_url = base_url
        elif self.provider == "lmstudio":
            self.base_url = cfg["lmstudio_url"]
        else:
            self.base_url = cfg["ollama_url"]
        
        logger.debug(f"OllamaClient initialized: provider={self.provider}, url={self.base_url}")

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
        """Get or create the shared httpx client."""
        if cls._shared_client is None or cls._shared_client.is_closed:
            cls._shared_client = httpx.AsyncClient(timeout=None)
        return cls._shared_client

    # ── Chat Streaming ──────────────────────────────────────────────

    async def stream_chat(
        self, 
        model: str, 
        messages: Messages
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat responses from the configured backend.
        
        Args:
            model: Name of the model to use
            messages: List of message dicts with 'role' and 'content'
            
        Yields:
            Text chunks from the model response
        """
        if self.provider == "lmstudio":
            async for chunk in self._stream_chat_openai(model, messages):
                yield chunk
        else:
            async for chunk in self._stream_chat_ollama(model, messages):
                yield chunk

    async def _stream_chat_ollama(
        self, model: str, messages: Messages
    ) -> AsyncGenerator[str, None]:
        """Stream chat via Ollama native API."""
        from utils.config_loader import get_config
        context_limit = get_config("CONTEXT_LIMIT", 8192)
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_ctx": context_limit
            }
        }
        
        client = self._get_client()
        try:
            async with client.stream(
                "POST", url, json=payload, timeout=None
            ) as response:
                if response.status_code != 200:
                    error_detail = ""
                    try:
                        async for chunk in response.aiter_text():
                            error_detail += chunk
                    except Exception:
                        pass
                    error_msg = (
                        f"Error: Ollama returned status {response.status_code}. "
                        f"Details: {error_detail}"
                    )
                    logger.error(error_msg)
                    yield error_msg
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "message" in data:
                            content = data["message"].get("content", "")
                            if content:
                                yield content
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON line: {line[:100]}...")
                        continue
                        
        except httpx.ConnectError as e:
            error_msg = (
                "Error: Could not connect to Ollama. "
                "Make sure 'ollama serve' is running."
            )
            logger.error(f"Connection error to Ollama: {e}")
            yield error_msg
            
        except httpx.RemoteProtocolError as e:
            error_msg = (
                "Error: Ollama connection closed unexpectedly. "
                "(Possible model crash or timeout)."
            )
            logger.error(f"Remote protocol error: {e}")
            yield error_msg
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Unexpected error in stream_chat: {e}", exc_info=True)
            yield error_msg

    async def _stream_chat_openai(
        self, model: str, messages: Messages
    ) -> AsyncGenerator[str, None]:
        """Stream chat via OpenAI-compatible API (LM Studio)."""
        from utils.config_loader import get_config
        context_limit = get_config("CONTEXT_LIMIT", 8192)
        
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": context_limit
        }
        
        client = self._get_client()
        try:
            async with client.stream(
                "POST", url, json=payload, timeout=None
            ) as response:
                if response.status_code != 200:
                    error_detail = ""
                    try:
                        async for chunk in response.aiter_text():
                            error_detail += chunk
                    except Exception:
                        pass
                    error_msg = (
                        f"Error: LM Studio returned status {response.status_code}. "
                        f"Details: {error_detail}"
                    )
                    logger.error(error_msg)
                    yield error_msg
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    
                    # SSE format: "data: {...}" or "data: [DONE]"
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
                        
        except httpx.ConnectError as e:
            error_msg = (
                "Error: Could not connect to LM Studio. "
                "Make sure LM Studio is running with a model loaded."
            )
            logger.error(f"Connection error to LM Studio: {e}")
            yield error_msg
            
        except httpx.RemoteProtocolError as e:
            error_msg = (
                "Error: LM Studio connection closed unexpectedly."
            )
            logger.error(f"Remote protocol error (LM Studio): {e}")
            yield error_msg
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Unexpected error in LM Studio stream_chat: {e}", exc_info=True)
            yield error_msg

    # ── Model Management ────────────────────────────────────────────

    async def load_model(self, model: str) -> bool:
        """
        Explicitly load a model with specific parameters from config.
        Particularly useful for LM Studio to set context length and flash attention.
        """
        from utils.config_loader import get_config
        context_limit = get_config("CONTEXT_LIMIT", 8192)
        
        if self.provider == "lmstudio":
            # For LM Studio: use the specific load endpoint
            # Note: This often requires the base URL to be adjusted if it points to /v1
            # Usually LM Studio API is on port 1234
            base = self.base_url.replace("/v1", "") if self.base_url.endswith("/v1") else self.base_url
            url = f"{base}/api/v1/models/load"
            
            payload = {
                "model": model,
                "context_length": context_limit,
                "flash_attention": True
            }
            try:
                client = self._get_client()
                response = await client.post(url, json=payload, timeout=300)
                if response.status_code == 200:
                    logger.info(f"Successfully loaded model in LM Studio: {model} with ctx {context_limit}")
                    return True
                else:
                    logger.warning(f"Failed to load model {model} in LM Studio: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                logger.error(f"Error loading model {model} in LM Studio: {e}")
                return False
                
        else:
            # For Ollama: We can just use the /api/generate endpoint with a tiny prompt and keep_alive
            # to pre-load the model into memory.
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": "",
                "keep_alive": "5m",
                "options": {
                    "num_ctx": context_limit
                }
            }
            try:
                client = self._get_client()
                response = await client.post(url, json=payload, timeout=60.0)
                if response.status_code == 200:
                    logger.info(f"Successfully pre-loaded model in Ollama: {model}")
                    return True
                else:
                    logger.warning(f"Failed to pre-load model {model} in Ollama: {response.text}")
                    return False
            except Exception as e:
                logger.error(f"Error pre-loading model {model} in Ollama: {e}")
                return False

    async def unload_model(self, model: str) -> bool:
        """
        Unload a model from memory.
        
        - LM Studio: POST /api/v1/models/unload with instance_id
        - Ollama: POST /api/chat with keep_alive=0
        """
        if self.provider == "lmstudio":
            base = self.base_url.replace("/v1", "") if self.base_url.endswith("/v1") else self.base_url
            url = f"{base}/api/v1/models/unload"
            payload = {
                "instance_id": model
            }
            try:
                client = self._get_client()
                response = await client.post(url, json=payload, timeout=30.0)
                if response.status_code == 200:
                    logger.info(f"Successfully unloaded model in LM Studio: {model}")
                    return True
                else:
                    logger.warning(f"Failed to unload model {model} in LM Studio: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                logger.warning(f"Failed to unload model {model} in LM Studio: {e}")
                return False
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "keep_alive": 0
        }
        try:
            client = self._get_client()
            await client.post(url, json=payload)
            logger.info(f"Successfully unloaded model: {model}")
            return True
        except Exception as e:
            logger.warning(f"Failed to unload model {model}: {e}")
            return False

    # ── Vision ──────────────────────────────────────────────────────

    async def describe_image(
        self, 
        model: str, 
        image_base64: str, 
        prompt: str = "Describe this image in detail."
    ) -> str:
        """
        Use a vision model to describe an image.
        """
        if self.provider == "lmstudio":
            return await self._describe_image_openai(model, image_base64, prompt)
        return await self._describe_image_ollama(model, image_base64, prompt)

    async def _describe_image_ollama(
        self, model: str, image_base64: str, prompt: str
    ) -> str:
        """Describe image via Ollama native API."""
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
            client = self._get_client()
            response = await client.post(url, json=payload, timeout=300)
            if response.status_code == 200:
                data = response.json()
                description = data.get("message", {}).get("content", "[No description]")
                # Strip thinking tags
                description = re.sub(r'<think>.*?</think>', '', description, flags=re.DOTALL)
                description = re.sub(r'<think>.*', '', description, flags=re.DOTALL)
                description = description.strip()
                logger.debug(f"Image described successfully with model {model}")
                return description
            else:
                error_msg = f"[Vision model error: {response.status_code}]"
                logger.error(f"Vision model error: {error_msg}")
                return error_msg
                    
        except httpx.ConnectError as e:
            logger.error(f"Connection error in describe_image: {e}")
            return "[Error: Could not connect to Ollama]"
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout in describe_image: {e}")
            return "[Error: Timeout processing the image]"
            
        except Exception as e:
            logger.error(f"Unexpected error in describe_image: {e}", exc_info=True)
            return f"[Error: {str(e)}]"

    async def _describe_image_openai(
        self, model: str, image_base64: str, prompt: str
    ) -> str:
        """Describe image via OpenAI-compatible API (LM Studio vision)."""
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "stream": False
        }
        
        try:
            client = self._get_client()
            response = await client.post(url, json=payload, timeout=300)
            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "[No description]")
                    # Strip thinking tags
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                    content = re.sub(r'<think>.*', '', content, flags=re.DOTALL)
                    content = content.strip()
                    logger.debug(f"Image described via LM Studio with model {model}")
                    return content
                return "[No description]"
            else:
                error_msg = f"[Vision model error: {response.status_code}]"
                logger.error(f"LM Studio vision error: {error_msg}")
                return error_msg
                    
        except httpx.ConnectError as e:
            logger.error(f"Connection error in LM Studio describe_image: {e}")
            return "[Error: Could not connect to LM Studio]"
            
        except httpx.TimeoutException as e:
            logger.error(f"Timeout in LM Studio describe_image: {e}")
            return "[Error: Timeout processing the image]"
            
        except Exception as e:
            logger.error(f"Unexpected error in LM Studio describe_image: {e}", exc_info=True)
            return f"[Error: {str(e)}]"

    # ── Embeddings ───────────────────────────────────────────────────

    async def generate_embedding(self, model: str, text: str) -> List[float]:
        """
        Generate embeddings for text using a specific model.
        
        Routes to the configured backend:
          - ollama: POST /api/embeddings
          - lmstudio: POST /v1/embeddings (OpenAI-compatible)
        """
        if self.provider == "lmstudio":
            return await self._embedding_openai(model, text)
        return await self._embedding_ollama(model, text)

    async def _embedding_ollama(self, model: str, text: str) -> List[float]:
        """Generate embedding via Ollama native API."""
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": model,
            "prompt": text
        }
        
        try:
            client = self._get_client()
            response = await client.post(url, json=payload, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding", [])
            else:
                logger.error(f"Embedding error {response.status_code}: {response.text}")
                return []
                    
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def _embedding_openai(self, model: str, text: str) -> List[float]:
        """Generate embedding via OpenAI-compatible API (LM Studio)."""
        url = f"{self.base_url}/v1/embeddings"
        payload = {
            "model": model,
            "input": text
        }
        
        try:
            client = self._get_client()
            response = await client.post(url, json=payload, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                embeddings = data.get("data", [])
                if embeddings:
                    return embeddings[0].get("embedding", [])
                return []
            else:
                logger.error(f"LM Studio embedding error {response.status_code}: {response.text}")
                return []
                    
        except Exception as e:
            logger.error(f"Error generating LM Studio embedding: {e}")
            return []
