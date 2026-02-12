"""Skill registry for reading and formatting skill definitions from SKILL.md files.

Supports progressive disclosure with three levels:
- Level 1: Metadata only (name + description)
- Level 2: SKILL.md content (instructions)
- Level 3: Additional files (EXAMPLES.md, REFERENCE.md, etc.)
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml

# from agent.config import SKILLS_DIR
PROJECT_ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"


class SkillRegistry:
    """Reads and manages skill definitions from SKILL.md files with progressive disclosure support."""

    def __init__(self):
        self.skills: Dict[str, Dict] = {}
        self.skill_dirs: Dict[str, Path] = {}
        self._discover_skills()

    def _parse_skill_markdown(self, skill_dir: Path) -> Optional[Dict]:
        """Parse SKILL.md file to extract YAML frontmatter and content.

        Args:
            skill_dir: Path to skill directory

        Returns:
            Dictionary with skill data (frontmatter + full content)
        """
        skill_md_path = skill_dir / "SKILL.md"
        if not skill_md_path.exists():
            return None

        try:
            with open(skill_md_path, "r") as f:
                content = f.read()

            # Extract YAML frontmatter (between --- delimiters)
            if not content.startswith("---"):
                return None

            lines = content.split("\n")
            end_index = None
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    end_index = i
                    break

            if end_index is None:
                return None

            # Extract and parse YAML frontmatter
            yaml_content = "\n".join(lines[1:end_index])
            frontmatter = yaml.safe_load(yaml_content) or {}

            # Get the markdown body (everything after the frontmatter)
            markdown_body = "\n".join(lines[end_index + 1:]).strip()

            return {
                **frontmatter,
                "content": markdown_body,
            }

        except Exception as e:
            print(f"Warning: Could not parse SKILL.md in {skill_dir}: {e}")
            return None

    def _discover_skills(self) -> None:
        """Discover all available skills by scanning skill directories."""
        # skill_names = ["arduino-mega-2560", "dht11", "mpu6050"]
        skill_names = [
            "arduino_setup", 
            "dht11-sensor", 
            # "mpu6050-imu", 
            # "timer-interrupt", 
            # "button-debounce"
        ]

        for skill_name in skill_names:
            skill_dir = SKILLS_DIR / skill_name
            if skill_dir.exists():
                skill_data = self._parse_skill_markdown(skill_dir)
                if skill_data:
                    self.skills[skill_name] = skill_data
                    self.skill_dirs[skill_name] = skill_dir
            else:
                raise ValueError(skill_dir)

    def get_available_skills(self) -> List[str]:
        """Get list of available skill names."""
        return list(self.skills.keys())

    def get_skill(self, skill_name: str) -> Optional[Dict]:
        """Get complete skill definition including YAML frontmatter and markdown content.

        Args:
            skill_name: Name of the skill

        Returns:
            Dictionary with skill data or None if not found
        """
        return self.skills.get(skill_name)

    # =========================================================================
    # Progressive Disclosure - Level 1: Metadata
    # =========================================================================

    def get_skill_metadata(self) -> str:
        """Get only skill metadata (name and description) for progressive disclosure.

        This is Level 1 - loaded at startup, minimal token cost.

        Returns:
            Formatted string with skill names and descriptions
        """
        metadata = []
        for skill_name in self.get_available_skills():
            skill = self.skills[skill_name]
            name = skill.get('name', skill_name)
            description = skill.get('description', 'No description available')
            metadata.append(f"- **{name}**: {description}")

        return "\n".join(metadata)

    # =========================================================================
    # Progressive Disclosure - Level 2: SKILL.md Content
    # =========================================================================

    def get_skill_content(self, skill_name: str) -> Optional[str]:
        """Get SKILL.md content for a specific skill (Level 2).

        Args:
            skill_name: Name of the skill

        Returns:
            SKILL.md content or None if not found
        """
        skill = self.get_skill(skill_name)
        if skill:
            return f"## {skill.get('name', skill_name)}\n\n{skill.get('content', '')}"
        return None

    # =========================================================================
    # Progressive Disclosure - Level 3: Additional Files
    # =========================================================================

    def get_skill_files(self, skill_name: str) -> List[str]:
        """Get list of additional files available for a skill (Level 3).

        Args:
            skill_name: Name of the skill

        Returns:
            List of additional file names (e.g., ['EXAMPLES.md', 'REFERENCE.md'])
        """
        if skill_name not in self.skill_dirs:
            return []

        skill_dir = self.skill_dirs[skill_name]
        files = []

        for file_path in skill_dir.iterdir():
            if file_path.is_file() and file_path.suffix == '.md' and file_path.name != 'SKILL.md':
                files.append(file_path.name)

        return sorted(files)

    def read_skill_file(self, skill_name: str, filename: str) -> Optional[str]:
        """Read an additional file from a skill directory (Level 3).

        Args:
            skill_name: Name of the skill
            filename: Name of the file to read (e.g., 'EXAMPLES.md')

        Returns:
            File content or None if not found
        """
        if skill_name not in self.skill_dirs:
            return None

        skill_dir = self.skill_dirs[skill_name]
        file_path = skill_dir / filename

        # Security: only allow .md files within the skill directory
        if not file_path.exists() or file_path.suffix != '.md':
            return None

        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not read {filename} in {skill_name}: {e}")
            return None

    def get_all_skill_files_info(self) -> str:
        """Get information about all available files across all skills.

        Returns:
            Formatted string listing skills and their additional files
        """
        info = []
        for skill_name in self.get_available_skills():
            files = self.get_skill_files(skill_name)
            if files:
                file_list = ', '.join(files)
                info.append(f"- **{skill_name}**: {file_list}")
            else:
                info.append(f"- **{skill_name}**: (no additional files)")

        return "\n".join(info)

    # =========================================================================
    # Legacy method (deprecated)
    # =========================================================================

    def get_skills_for_prompt(self) -> str:
        """Get formatted skills for inclusion in Claude prompt (full disclosure - deprecated).

        This loads all skill content at once. Use get_skill_metadata() for
        progressive disclosure instead.

        Returns:
            Formatted string with all skills for prompt context
        """
        formatted_skills = []
        for skill_name in self.get_available_skills():
            skill = self.skills[skill_name]
            formatted_skills.append(f"## {skill.get('name', skill_name)}\n\n{skill.get('content', '')}")

        return "\n\n".join(formatted_skills)
