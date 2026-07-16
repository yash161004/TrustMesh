import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.llm_client import FallbackLLMClient

@pytest.mark.asyncio
async def test_fallback_success_on_second_provider():
    # Setup mock clients
    mock_groq = MagicMock()
    mock_groq.generate = AsyncMock(side_effect=httpx.HTTPStatusError(message="429 Too Many Requests", request=MagicMock(), response=MagicMock()))
    
    mock_gemini = MagicMock()
    mock_gemini.generate = AsyncMock(return_value="Gemini response")
    
    mock_mock = MagicMock()
    mock_mock.generate = AsyncMock(return_value="Mock response")
    
    with patch("app.llm_client.get_settings"):
        client = FallbackLLMClient([])
        client.clients = [
            ("groq", mock_groq),
            ("gemini", mock_gemini),
            ("mock", mock_mock)
        ]
        
        result = await client.generate([{"role": "user", "content": "hello"}])
        
        assert result == "Gemini response"
        assert client.last_used_provider == "gemini"
        mock_groq.generate.assert_called_once()
        mock_gemini.generate.assert_called_once()
        mock_mock.generate.assert_not_called()

@pytest.mark.asyncio
async def test_fallback_all_fail():
    mock_groq = MagicMock()
    mock_groq.generate = AsyncMock(side_effect=httpx.HTTPStatusError(message="429", request=MagicMock(), response=MagicMock()))
    
    mock_gemini = MagicMock()
    mock_gemini.generate = AsyncMock(side_effect=httpx.HTTPStatusError(message="500", request=MagicMock(), response=MagicMock()))
    
    mock_mock = MagicMock()
    mock_mock.generate = AsyncMock(return_value="Mock response")
    
    with patch("app.llm_client.get_settings"):
        client = FallbackLLMClient([])
        client.clients = [
            ("groq", mock_groq),
            ("gemini", mock_gemini),
            ("mock", mock_mock)
        ]
        
        result = await client.generate([{"role": "user", "content": "hello"}])
        
        assert result == "Mock response"
        assert client.last_used_provider == "mock"
        mock_groq.generate.assert_called_once()
        mock_gemini.generate.assert_called_once()
        mock_mock.generate.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_stream_success_on_second_provider():
    mock_groq = MagicMock()
    
    async def mock_groq_stream(*args, **kwargs):
        raise httpx.HTTPStatusError(message="429", request=MagicMock(), response=MagicMock())
        yield "never"
    
    mock_groq.generate_stream = mock_groq_stream
    
    mock_gemini = MagicMock()
    
    async def mock_gemini_stream(*args, **kwargs):
        yield "Gemini"
        yield " stream"
        
    mock_gemini.generate_stream = mock_gemini_stream
    
    with patch("app.llm_client.get_settings"):
        client = FallbackLLMClient([])
        client.clients = [
            ("groq", mock_groq),
            ("gemini", mock_gemini)
        ]
        
        chunks = []
        async for chunk in client.generate_stream([{"role": "user", "content": "hello"}]):
            chunks.append(chunk)
            
        assert "".join(chunks) == "Gemini stream"
        assert client.last_used_provider == "gemini"

@pytest.mark.asyncio
async def test_fallback_success_on_third_provider():
    mock_groq = MagicMock()
    mock_groq.generate = AsyncMock(side_effect=httpx.HTTPStatusError(message="429", request=MagicMock(), response=MagicMock()))
    
    mock_gemini = MagicMock()
    mock_gemini.generate = AsyncMock(side_effect=httpx.HTTPStatusError(message="503", request=MagicMock(), response=MagicMock()))
    
    mock_openrouter = MagicMock()
    mock_openrouter.generate = AsyncMock(return_value="OpenRouter response")
    
    mock_mock = MagicMock()
    mock_mock.generate = AsyncMock(return_value="Mock response")
    
    with patch("app.llm_client.get_settings"):
        client = FallbackLLMClient([])
        client.clients = [
            ("groq", mock_groq),
            ("gemini", mock_gemini),
            ("openrouter", mock_openrouter),
            ("mock", mock_mock)
        ]
        
        result = await client.generate([{"role": "user", "content": "hello"}])
        
        assert result == "OpenRouter response"
        assert client.last_used_provider == "openrouter"
        mock_groq.generate.assert_called_once()
        mock_gemini.generate.assert_called_once()
        mock_openrouter.generate.assert_called_once()
        mock_mock.generate.assert_not_called()
