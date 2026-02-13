"""Planner module: Decomposes user questions into sub-tasks."""
import json
import logging
from typing import List, Dict, Any
import uuid

from src.services.deep_research.models import ResearchTask, TaskStatus

logger = logging.getLogger(__name__)


class Planner:
    """Breaks down complex research questions into manageable sub-tasks."""
    
    def __init__(self, llm_client):
        self.client = llm_client
    
    async def create_research_plan(self, question: str, model: str) -> List[ResearchTask]:
        """
        Decompose the main question into sub-tasks.
        
        Args:
            question: The original research question
            model: LLM model to use
            
        Returns:
            List of ResearchTask objects
        """
        prompt = self._create_planning_prompt(question)
        
        try:
            response = await self._get_llm_response(prompt, model)
            tasks_data = self._parse_plan_response(response)
            
            tasks = []
            for i, task_data in enumerate(tasks_data):
                task = ResearchTask(
                    id=str(uuid.uuid4())[:8],
                    query=task_data["query"],
                    priority=task_data.get("priority", i + 1),
                    status=TaskStatus.PENDING
                )
                tasks.append(task)
            
            logger.info(f"Planner created {len(tasks)} tasks for question: {question[:50]}...")
            return tasks
            
        except Exception as e:
            logger.error(f"Error in planner: {e}")
            # Fallback: create a single task with the original question
            return [ResearchTask(
                id=str(uuid.uuid4())[:8],
                query=question,
                priority=1,
                status=TaskStatus.PENDING
            )]
    
    def _create_planning_prompt(self, question: str) -> str:
        """Create the planning prompt for the LLM."""
        return f"""You are a Research Planning Agent. Your task is to decompose a complex research question into specific, actionable sub-tasks.

Original Question: {question}

Break this down into 3-7 specific sub-tasks or sub-questions that need to be investigated to fully answer the original question.

For each sub-task, provide:
1. A specific search query (use keywords, not full sentences)
2. A priority (1 = highest priority, higher numbers = lower priority)

Respond ONLY with a valid JSON array in this format:
[
  {{
    "query": "keywords for search",
    "priority": 1
  }},
  {{
    "query": "another search query",
    "priority": 2
  }}
]

Guidelines:
- Queries should be keyword-based for better search results
- Cover different aspects of the topic
- Order by logical dependency (some questions may need to be answered first)
- Be specific, not vague
- Maximum 7 sub-tasks
"""
    
    async def _get_llm_response(self, prompt: str, model: str) -> str:
        """Get response from LLM."""
        messages = [{"role": "user", "content": prompt}]
        full_response = ""
        
        async for chunk in self.client.stream_chat(model, messages):
            full_response += chunk
        
        return full_response.strip()
    
    def _parse_plan_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON response from LLM."""
        # Clean up response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "tasks" in data:
                return data["tasks"]
            else:
                logger.warning(f"Unexpected response format: {data}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nResponse: {response[:200]}")
            return []
