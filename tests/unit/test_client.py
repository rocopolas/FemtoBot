"""Unit tests for client module (Ollama client)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from src.client import OllamaClient


class TestOllamaClient:
    """Test suite for Ollama client."""
    
    @pytest.fixture(autouse=True)
    def reset_shared_client(self):
        """Reset shared client before and after each test."""
        OllamaClient._shared_client = None
        yield
        OllamaClient._shared_client = None
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return OllamaClient(base_url="http://localhost:11434")
    
    @pytest.mark.asyncio
    @patch('src.client.get_config', return_value=8192)
    async def test_stream_chat_success(self, mock_get_config, client):
        """Test successful streaming chat."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        class AsyncIterator:
            def __init__(self, data):
                self.data = iter(data)
            def __aiter__(self):
                return self
            async def __anext__(self):
                try:
                    return next(self.data)
                except StopIteration:
                    raise StopAsyncIteration

        mock_response.aiter_lines = MagicMock(return_value=AsyncIterator([
            json.dumps({"message": {"content": "Hello"}, "done": False}),
            json.dumps({"message": {"content": " world"}, "done": True}),
        ]))
        
        # Create async context manager mock for stream
        stream_context = AsyncMock()
        stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        stream_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch("src.client.httpx.AsyncClient") as mock_client_cls:
            mock_instance = mock_client_cls.return_value
            mock_instance.is_closed = False
            mock_instance.stream = MagicMock(return_value=stream_context)
            
            chunks = []
            async for chunk in client.stream_chat("test-model", [{"role": "user", "content": "Hi"}]):
                chunks.append(chunk)
            
            assert "Hello" in "".join(chunks)
    
    @pytest.mark.asyncio
    @patch('src.client.get_config', return_value=8192)
    async def test_stream_chat_connection_error(self, mock_get_config, client):
        """Test handling of connection error."""
        with patch("src.client.httpx.AsyncClient") as mock_client_cls:
            mock_instance = mock_client_cls.return_value
            mock_instance.is_closed = False
            mock_instance.stream = MagicMock(side_effect=Exception("Connection refused"))
            
            chunks = []
            async for chunk in client.stream_chat("test-model", []):
                chunks.append(chunk)
            
            assert any("Error" in chunk for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_describe_image(self, client):
        """Test image description."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # The Ollama API returns response in {"response": "..."} format for generate endpoint
        mock_response.json.return_value = {"response": "A cat"}
        
        with patch("src.client.httpx.AsyncClient") as mock_client_cls:
            mock_instance = mock_client_cls.return_value
            mock_instance.is_closed = False
            mock_instance.post = AsyncMock(return_value=mock_response)
            
            result = await client.describe_image("vision-model", "base64data", "Describe this")
            assert result == "A cat"
    
    @pytest.mark.asyncio
    async def test_unload_model(self, client):
        """Test model unloading."""
        with patch("src.client.httpx.AsyncClient") as mock_client_cls:
            mock_instance = mock_client_cls.return_value
            mock_instance.is_closed = False
            mock_instance.post = AsyncMock(return_value=MagicMock())
            
            result = await client.unload_model("test-model")
            assert result == True
