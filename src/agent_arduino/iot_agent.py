"""IoT Agent orchestrator using Anthropic API with progressive skill disclosure.

Implements three-level progressive disclosure:
- Level 1: Skill metadata (name + description) in system prompt
- Level 2: SKILL.md content via read_skill tool
- Level 3: Additional files (EXAMPLES.md, etc.) via read_skill_file tool
"""

from typing import Dict, Any, List
import re

from anthropic import Anthropic

from src.agent_arduino.config import config
ANTHROPIC_API_KEY = config.ANTHROPIC_API_KEY
ANTHROPIC_MODEL = config.ANTHROPIC_MODEL
from agent_arduino.skill_registry import SkillRegistry


def extract_code_from_response(response: str) -> str:
    """Extract code from markdown code blocks in the response.

    Args:
        response: The full response text from Claude

    Returns:
        Extracted code, or original response if no code block found
    """
    # Match ```cpp, ```c, ```arduino, or just ``` code blocks
    pattern = r'```(?:cpp|c|arduino|ino)?\s*\n(.*?)```'
    matches = re.findall(pattern, response, re.DOTALL)

    if matches:
        # Return the last code block (usually the complete firmware)
        return matches[-1].strip()

    # Fallback: return original response
    return response.strip()


# Tool definitions for progressive skill disclosure
SKILL_TOOLS = [
    {
        "name": "read_skill",
        "description": "Read the main SKILL.md content for a specific skill. Use this to get detailed instructions and patterns for a skill.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to read"
                }
            },
            "required": ["skill_name"]
        }
    },
    {
        "name": "read_skill_file",
        "description": "Read an additional reference file from a skill directory. Use this to get detailed examples, API references, or specialized guides.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill directory"
                },
                "filename": {
                    "type": "string",
                    "description": "Name of the file to read (e.g., 'EXAMPLES.md', 'SENSORS.md')"
                }
            },
            "required": ["skill_name", "filename"]
        }
    },
    {
        "name": "list_skill_files",
        "description": "List additional files available in a skill directory. Use this to discover what reference materials are available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to list files for"
                }
            },
            "required": ["skill_name"]
        }
    }
]


class IoTAgent:
    """Main agent for orchestrating IoT firmware generation with progressive skill disclosure."""

    def __init__(self, framework: str):
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        assert framework in ["ESP-IDF", "Arduino"]
        self.framework = framework
        self.skill_registry = SkillRegistry()
        self.model = ANTHROPIC_MODEL
        self.messages = []

    def run(self, task: str) -> Dict[str, Any]:
        """Run the IoT agent on a design task using progressive skill disclosure.

        Uses tool use to let Claude read skill content on-demand:
        - Level 1: Skill metadata in system prompt (always loaded)
        - Level 2: Claude calls read_skill() to get SKILL.md content
        - Level 3: Claude calls read_skill_file() for additional files

        Args:
            task: User's firmware design task description

        Returns:
            Dictionary containing generated firmware
        """
        self.messages = []
        print(f"\n[Agent] Processing task: {task}\n")

        # Build system prompt with Level 1 metadata
        system_prompt = self._build_system_prompt()
        print(f"\n[Agent] System Prompt: {system_prompt}\n")

        # Add user task
        self.messages.append({"role": "user", "content": task})

        # Run agentic loop with tool use
        raw_response = self._run_agent_loop(system_prompt)

        # Extract code from markdown code blocks
        firmware = extract_code_from_response(raw_response)

        print("[Agent] Firmware generation complete\n")

        return {
            "task": task,
            "firmware": firmware,
        }

    def _build_system_prompt(self) -> str:
        """Build system prompt with Level 1 skill metadata only.

        Progressive disclosure levels:
        - Level 1 (here): Only skill names and descriptions
        - Level 2: SKILL.md content - loaded via read_skill tool
        - Level 3: Additional files - discovered from SKILL.md, loaded via read_skill_file
        """
        return f"""You are an IoT firmware design expert. Generate complete {self.framework} firmware code based on user requirements.

## Available Skills

The following skills are available. Use the read_skill tool to load their instructions:

{self.skill_registry.get_skill_metadata()}

## Workflow

1. Analyze the user's requirements
2. Use read_skill to load relevant skill instructions
3. SKILL.md files reference additional files (like EXAMPLES.md, SENSORS.md) - use read_skill_file to load them if needed
4. Generate complete, working {self.framework} firmware

## Output Requirements

When generating final firmware, wrap your {self.framework} code in a markdown code block:
- Use \`\`\`cpp to start and \`\`\` to end
- You may include brief explanation before the code block
- The code inside the block must be complete, compilable {self.framework} code"""

    def _run_agent_loop(self, system_prompt: str) -> str:
        """Run the agentic loop with tool use for progressive disclosure."""
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            print(f"[Agent] Iteration {iteration}: Calling Claude API...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=self.messages,
                tools=SKILL_TOOLS,
                timeout=60.0,
            )

            # Check if we're done (no more tool calls)
            if response.stop_reason == "end_turn":
                # Extract the final text response
                for block in response.content:
                    if hasattr(block, 'text'):
                        return block.text
                return ""

            # Process tool calls
            tool_calls_made = False
            assistant_content = []
            print(f"[Agent] Response content: {response.content}")
            # exit(0)
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls_made = True
                    tool_result = self._handle_tool_call(block.name, block.input)
                    print(f"[Agent] Tool: {block.name}({block.input}) -> {len(tool_result)} chars")

                    assistant_content.append(block)

            if tool_calls_made:
                # Add assistant message with tool calls
                self.messages.append({"role": "assistant", "content": assistant_content})

                # Add tool results
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        result = self._handle_tool_call(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                self.messages.append({"role": "user", "content": tool_results})
            else:
                # No tool calls, extract text and return
                for block in response.content:
                    if hasattr(block, 'text'):
                        return block.text
                return ""

        print("[Agent] Warning: Max iterations reached")
        return ""

    def _handle_tool_call(self, tool_name: str, tool_input: Dict) -> str:
        """Handle a tool call and return the result."""
        if tool_name == "read_skill":
            skill_name = tool_input.get("skill_name", "")
            content = self.skill_registry.get_skill_content(skill_name)
            if content:
                return content
            return f"Error: Skill '{skill_name}' not found. Available: {', '.join(self.skill_registry.get_available_skills())}"

        elif tool_name == "read_skill_file":
            skill_name = tool_input.get("skill_name", "")
            filename = tool_input.get("filename", "")
            content = self.skill_registry.read_skill_file(skill_name, filename)
            if content:
                return content
            available = self.skill_registry.get_skill_files(skill_name)
            return f"Error: File '{filename}' not found in '{skill_name}'. Available files: {', '.join(available) or 'none'}"

        elif tool_name == "list_skill_files":
            skill_name = tool_input.get("skill_name", "")
            files = self.skill_registry.get_skill_files(skill_name)
            if files:
                return f"Available files in {skill_name}: {', '.join(files)}"
            return f"No additional files found in '{skill_name}'"

        return f"Error: Unknown tool '{tool_name}'"
