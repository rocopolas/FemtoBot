"""Critic module: Evaluates research quality and controls the loop."""
import json
import logging
from typing import List, Optional, Tuple
import uuid

from src.services.deep_research.models import (
    ResearchContext, 
    ResearchTask, 
    TaskStatus,
    Chunk,
    GapAnalysis,
    IterationDecision
)

logger = logging.getLogger(__name__)


class Critic:
    """Evaluates research progress and determines next steps."""
    
    def __init__(self, llm_client, min_chunks_per_task: int = 2):
        self.client = llm_client
        self.min_chunks_per_task = min_chunks_per_task
    
    async def evaluate_task(
        self, 
        task: ResearchTask, 
        chunks: List[Chunk],
        context: ResearchContext,
        model: str
    ) -> Tuple[IterationDecision, Optional[GapAnalysis]]:
        """
        Evaluate if a task has sufficient information.
        
        Args:
            task: The task being evaluated
            chunks: Chunks extracted for this task
            context: Full research context
            model: LLM model to use
            
        Returns:
            Tuple of (decision, gap_analysis if decision is CONTINUE)
        """
        logger.info(f"Critic evaluating task {task.id} with {len(chunks)} chunks")
        
        # Quick check: minimum chunks threshold
        if len(chunks) < self.min_chunks_per_task:
            gap = GapAnalysis(
                has_gaps=True,
                missing_aspects=["Insufficient sources found"],
                suggested_queries=[f"{task.query} more details"],
                reasoning="Not enough sources found for this task"
            )
            return IterationDecision.CONTINUE, gap
        
        # LLM-based evaluation
        prompt = self._create_evaluation_prompt(task, chunks, context)
        
        try:
            response = await self._get_llm_response(prompt, model)
            evaluation = self._parse_evaluation_response(response)
            
            if evaluation["sufficient"]:
                logger.info(f"Critic: Task {task.id} has sufficient information")
                return IterationDecision.FINISH, None
            else:
                # Perform gap analysis
                gap = await self._analyze_gaps(
                    task, chunks, evaluation["reasoning"], context, model
                )
                logger.info(f"Critic: Task {task.id} has gaps - {len(gap.suggested_queries)} new queries suggested")
                return IterationDecision.CONTINUE, gap
                
        except Exception as e:
            logger.error(f"Error in critic evaluation: {e}")
            # Conservative: assume we need more info
            gap = GapAnalysis(
                has_gaps=True,
                missing_aspects=["Evaluation error"],
                suggested_queries=[task.query],
                reasoning=f"Error during evaluation: {e}"
            )
            return IterationDecision.CONTINUE, gap
    
    async def evaluate_final(
        self, 
        context: ResearchContext, 
        model: str
    ) -> Tuple[bool, List[ResearchTask]]:
        """
        Final evaluation when max iterations reached or all tasks complete.
        
        Args:
            context: Full research context
            model: LLM model to use
            
        Returns:
            Tuple of (should_continue, additional_tasks if should_continue)
        """
        prompt = self._create_final_evaluation_prompt(context)
        
        try:
            response = await self._get_llm_response(prompt, model)
            evaluation = self._parse_evaluation_response(response)
            
            if evaluation["sufficient"]:
                return False, []
            else:
                # Generate emergency tasks
                gap = await self._analyze_gaps_final(context, evaluation["reasoning"], model)
                additional_tasks = self._create_tasks_from_gap(gap, context)
                return True, additional_tasks
                
        except Exception as e:
            logger.error(f"Error in final evaluation: {e}")
            return False, []
    
    async def _analyze_gaps(
        self, 
        task: ResearchTask, 
        chunks: List[Chunk],
        evaluation_reasoning: str,
        context: ResearchContext,
        model: str
    ) -> GapAnalysis:
        """Analyze what information is missing."""
        prompt = self._create_gap_analysis_prompt(task, chunks, evaluation_reasoning, context)
        
        try:
            response = await self._get_llm_response(prompt, model)
            # CORRECCIÓN: _parse_gap_response ya devuelve un objeto GapAnalysis.
            # No intentes acceder a él como si fuera un dict con .get()
            return self._parse_gap_response(response)
            
        except Exception as e:
            logger.error(f"Error in gap analysis: {e}")
            # MEJORA DEL FALLBACK:
            # En lugar de agregar "alternative" ciegamente, intentamos una estrategia
            # más limpia o simplemente devolvemos la query original con una nota.
            
            # Evitamos el bucle "alternative alternative" verificando si ya existe
            new_query = f"{task.query} specific details"
            if "specific details" in task.query:
                 new_query = task.query # Si ya lo intentamos, no lo empeoramos
            
            return GapAnalysis(
                has_gaps=True,
                missing_aspects=["Analysis error"],
                suggested_queries=[new_query],
                reasoning=f"Error during gap analysis: {e}"
            )
    
    async def _analyze_gaps_final(
        self, 
        context: ResearchContext,
        reasoning: str,
        model: str
    ) -> GapAnalysis:
        """Final gap analysis when research is incomplete."""
        prompt = f"""You are a Gap Analysis Agent. The research is ending but may be incomplete.

Original Question: {context.original_question}

Total chunks collected: {len(context.chunks)}
Iterations completed: {context.iteration_count}/{context.max_iterations}

Previous evaluation: {reasoning}

Identify what critical information is still missing and suggest 2-3 focused search queries to find it.

Respond ONLY with a valid JSON object:
{{
  "missing_aspects": ["aspect 1", "aspect 2"],
  "suggested_queries": ["query 1", "query 2", "query 3"],
  "reasoning": "explanation"
}}
"""
        try:
            response = await self._get_llm_response(prompt, model)
            return self._parse_gap_response(response)
        except Exception as e:
            return GapAnalysis(
                has_gaps=True,
                missing_aspects=["Unknown"],
                suggested_queries=[context.original_question],
                reasoning=str(e)
            )
    
    def _create_tasks_from_gap(
        self, 
        gap: GapAnalysis, 
        context: ResearchContext
    ) -> List[ResearchTask]:
        """Create new tasks from gap analysis."""
        tasks = []
        for i, query in enumerate(gap.suggested_queries[:3]):  # Max 3 emergency tasks
            task = ResearchTask(
                id=str(uuid.uuid4())[:8],
                query=query,
                priority=99,  # High priority (emergency)
                status=TaskStatus.PENDING
            )
            tasks.append(task)
        return tasks
    
    def _create_evaluation_prompt(
        self, 
        task: ResearchTask, 
        chunks: List[Chunk],
        context: ResearchContext
    ) -> str:
        """Create evaluation prompt for a task."""
        chunks_text = "\n\n".join([
            f"Chunk {i+1} (relevance: {c.relevance_score}):\n{c.content[:300]}..."
            for i, c in enumerate(chunks)
        ])
        
        return f"""You are a Research Quality Critic. Evaluate if the collected information is sufficient to answer the task.

Original Question: {context.original_question}
Task: {task.query}

Collected Chunks ({len(chunks)}):
{chunks_text}

Evaluate:
1. Coverage: Does this cover all aspects of the task?
2. Quality: Is the information reliable and detailed?
3. Relevance: Are the chunks actually relevant to the task?

Respond ONLY with a valid JSON object:
{{
  "sufficient": true/false,
  "reasoning": "detailed explanation of your evaluation",
  "confidence": 0.0-1.0
}}

Be strict. Only mark as sufficient if you have high-quality, comprehensive information.
"""
    
    def _create_final_evaluation_prompt(self, context: ResearchContext) -> str:
        """Create final evaluation prompt for entire research."""
        all_chunks = context.get_all_completed_chunks()
        chunks_summary = f"Total chunks: {len(all_chunks)}\n"
        chunks_summary += f"Tasks completed: {len([t for t in context.tasks if t.status == TaskStatus.COMPLETED])}/{len(context.tasks)}\n"
        
        # Sample of chunks
        sample = "\n\n".join([
            f"- {c.content[:200]}... (from: {c.source.title})"
            for c in all_chunks[:5]
        ])
        
        return f"""You are a Final Research Evaluator. The research session is ending.

Original Question: {context.original_question}

Research Summary:
{chunks_summary}

Sample of collected information:
{sample}

Can the original question be answered comprehensively with this information?

Respond ONLY with a valid JSON object:
{{
  "sufficient": true/false,
  "reasoning": "explanation",
  "confidence": 0.0-1.0
}}
"""
    
    def _create_gap_analysis_prompt(
        self,
        task: ResearchTask,
        chunks: List[Chunk],
        evaluation_reasoning: str,
        context: ResearchContext
    ) -> str:
        """Create gap analysis prompt."""
        return f"""You are a Gap Analysis Agent. The information collected is insufficient.

Task: {task.query}
Evaluation: {evaluation_reasoning}

Analyze what's missing and suggest specific search queries to find it.

Respond ONLY with a valid JSON object:
{{
  "missing_aspects": ["specific aspect 1", "specific aspect 2"],
  "suggested_queries": ["query 1", "query 2"],
  "reasoning": "why these aspects are missing and how to find them"
}}

Guidelines:
- Queries should be different from the original task query
- Be specific about what's missing
- Suggest 2-3 targeted queries
"""
    
    async def _get_llm_response(self, prompt: str, model: str) -> str:
        """Get response from LLM."""
        messages = [{"role": "user", "content": prompt}]
        full_response = ""
        
        async for chunk in self.client.stream_chat(model, messages):
            full_response += chunk
        
        return full_response.strip()
    
    def _parse_evaluation_response(self, response: str) -> dict:
        """Parse evaluation JSON response."""
        response = self._clean_json_response(response)
        
        try:
            data = json.loads(response)
            return {
                "sufficient": data.get("sufficient", False),
                "reasoning": data.get("reasoning", ""),
                "confidence": data.get("confidence", 0.0)
            }
        except json.JSONDecodeError:
            logger.error(f"Failed to parse evaluation: {response[:200]}")
            return {"sufficient": False, "reasoning": "Parse error", "confidence": 0.0}
    
    def _parse_gap_response(self, response: str) -> GapAnalysis:
        """Parse gap analysis JSON response."""
        response = self._clean_json_response(response)
        
        try:
            data = json.loads(response)
            return GapAnalysis(
                has_gaps=True,
                missing_aspects=data.get("missing_aspects", []),
                suggested_queries=data.get("suggested_queries", []),
                reasoning=data.get("reasoning", "")
            )
        except json.JSONDecodeError:
            logger.error(f"Failed to parse gap analysis: {response[:200]}")
            return GapAnalysis(
                has_gaps=True,
                missing_aspects=["Parse error"],
                suggested_queries=[],
                reasoning="Failed to parse response"
            )
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response from markdown formatting."""
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()
