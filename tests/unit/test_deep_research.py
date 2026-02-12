
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import json
from src.services.deep_research_service import DeepResearchService
from src.constants import PROJECT_ROOT

@pytest.mark.asyncio
async def test_odt_generation():
    service = DeepResearchService()
    file_path = "test_report.odt"
    markdown_content = "# Title\n\n## Section\n\n- Item 1\n- Item 2\n\n**Bold Text**"
    
    try:
        service._create_odt("Test Topic", markdown_content, file_path)
        assert os.path.exists(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@pytest.mark.asyncio
async def test_deep_research_service_logic():
    service = DeepResearchService()
    
    # Mock internal helper methods to test the flow control
    service._get_llm_json_response = AsyncMock(side_effect=[
        {"action": "search", "query": "python 3.12 features", "thought": "Need info"},
        {"action": "finish", "thought": "Done"}
    ])
    
    service._summarize_results = AsyncMock(return_value="Python 3.12 is faster.")
    service._generate_report_markdown = AsyncMock(return_value="# Report\n\n- Python 3.12 is great.")
    
    # Mock BraveSearch
    with patch("src.services.deep_research_service.BraveSearch.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = "Search results for python 3.12"
        
        # Run research
        chat_id = 123
        topic = "Python 3.12"
        
        # Mock callback
        callback = AsyncMock()
        
        file_path = await service.research(topic, chat_id, callback)
        
        # Assertions
        assert mock_search.call_count == 1, "Should have searched once"
        mock_search.assert_called_with("python 3.12 features", count=3)
        
        assert service._get_llm_json_response.call_count == 2, "Should have called LLM for decision twice"
        
        assert os.path.exists(file_path)
        assert file_path.endswith(".odt")
        
        # Check if callback was called
        assert callback.called
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
