"""Skill loader for FemtoBot.
Parases SKILL.md files from the skills directory and combines them into a system prompt block.
"""
import os
import logging
from src.constants import PROJECT_ROOT

logger = logging.getLogger(__name__)

SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills")


def load_all_skills() -> str:
    """
    Search for all SKILL.md files in the skills directory and its immediate children.
    
    Returns:
        A combined markdown string of all loaded skills, or an empty string if none found.
    """
    if not os.path.exists(SKILLS_DIR):
        try:
            os.makedirs(SKILLS_DIR, exist_ok=True)
            logger.info(f"Created skills directory at {SKILLS_DIR}")
        except Exception as e:
            logger.error(f"Failed to create skills directory: {e}")
            return ""

    skills_dict = {}
    
    # We walk the directory to support both flat and nested skill structures
    # e.g., skills/weather/SKILL.md or skills/my_custom_skill/SKILL.md
    for root, dirs, files in os.walk(SKILLS_DIR):
        for filename in files:
            if filename.lower() == "skill.md":
                skill_path = os.path.join(root, filename)
                
                # Get the skill name from the folder name (or 'root' if in the main directory)
                if root == SKILLS_DIR:
                    skill_name = "Global Skill"
                else:
                    skill_name = os.path.basename(root).replace("_", " ").title()
                
                try:
                    with open(skill_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            skills_dict[skill_name] = content
                            logger.info(f"Loaded skill file: {skill_name}")
                except Exception as e:
                    logger.error(f"Error loading skill file {skill_path}: {e}")

    return skills_dict
