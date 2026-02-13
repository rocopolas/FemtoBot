import pytest
import os
import sys

# Añadir el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.services.deep_research_service import DeepResearchService


@pytest.mark.asyncio
async def test_odt_generation():
    """Test ODT file generation from markdown."""
    service = DeepResearchService()
    file_path = "test_report.odt"
    markdown_content = "# Title\n\n## Section\n\n- Item 1\n- Item 2\n\n**Bold Text**\n\n## References\n\n[1] Source Title - https://example.com"
    
    try:
        result_path = service._create_odt_report("Test Topic", markdown_content)
        assert os.path.exists(result_path)
        assert result_path.endswith(".odt")
        
        # Cleanup
        if os.path.exists(result_path):
            os.remove(result_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.mark.asyncio
async def test_research_service_initialization():
    """Test that the service initializes correctly with new architecture."""
    service = DeepResearchService()
    
    assert service.max_iterations == 15
    assert service.search_count == 5
    assert service.client is not None
    assert service.model is not None


@pytest.mark.asyncio
async def test_deep_research_models():
    """Test the data models used in deep research."""
    from src.services.deep_research.models import (
        ResearchTask, Source, Chunk, ResearchContext, TaskStatus
    )
    from datetime import datetime
    
    # Test ResearchTask
    task = ResearchTask(
        id="test123",
        query="test query",
        priority=1,
        status=TaskStatus.PENDING
    )
    assert task.id == "test123"
    assert task.status == TaskStatus.PENDING
    
    # Test Source
    source = Source(
        url="https://example.com",
        title="Example",
        description="Test description",
        task_id="test123"
    )
    assert source.url == "https://example.com"
    
    # Test Chunk
    chunk = Chunk(
        content="Test content",
        source=source,
        relevance_score=0.8,
        extracted_at=datetime.now(),
        task_id="test123"
    )
    assert chunk.relevance_score == 0.8
    
    # Test ResearchContext
    context = ResearchContext(
        original_question="Test question",
        max_iterations=15
    )
    assert context.original_question == "Test question"
    assert context.get_pending_tasks() == []


@pytest.mark.asyncio
async def test_planner_module():
    """Test the Planner module initialization."""
    from unittest.mock import MagicMock
    from src.services.deep_research.planner import Planner
    
    mock_client = MagicMock()
    planner = Planner(mock_client)
    
    assert planner.client == mock_client


@pytest.mark.asyncio
async def test_hunter_module():
    """Test the Hunter module initialization."""
    from src.services.deep_research.hunter import Hunter
    
    hunter = Hunter(search_count=5)
    assert hunter.search_count == 5


@pytest.mark.asyncio
async def test_reader_module():
    """Test the Reader module initialization."""
    from unittest.mock import MagicMock
    from src.services.deep_research.reader import Reader
    
    mock_client = MagicMock()
    reader = Reader(mock_client, min_relevance=0.7)
    
    assert reader.client == mock_client
    assert reader.min_relevance == 0.7


@pytest.mark.asyncio
async def test_critic_module():
    """Test the Critic module initialization."""
    from unittest.mock import MagicMock
    from src.services.deep_research.critic import Critic
    
    mock_client = MagicMock()
    critic = Critic(mock_client, min_chunks_per_task=2)
    
    assert critic.client == mock_client
    assert critic.min_chunks_per_task == 2


@pytest.mark.asyncio
async def test_writer_module():
    """Test the Writer module initialization."""
    from unittest.mock import MagicMock
    from src.services.deep_research.writer import Writer
    
    mock_client = MagicMock()
    writer = Writer(mock_client)
    
    assert writer.client == mock_client


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test the Orchestrator initialization."""
    from unittest.mock import MagicMock
    from src.services.deep_research.orchestrator import DeepResearchOrchestrator
    
    mock_client = MagicMock()
    orchestrator = DeepResearchOrchestrator(
        llm_client=mock_client,
        model="test-model",
        max_iterations=15,
        search_count=5
    )
    
    assert orchestrator.client == mock_client
    assert orchestrator.model == "test-model"
    assert orchestrator.max_iterations == 15
    assert orchestrator.search_count == 5
    
    # Check all modules are initialized
    assert orchestrator.planner is not None
    assert orchestrator.hunter is not None
    assert orchestrator.reader is not None
    assert orchestrator.critic is not None
    assert orchestrator.writer is not None
