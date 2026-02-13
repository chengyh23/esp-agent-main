#!/usr/bin/env python3
"""Batch evaluation script for IoT agent.

Reads tasks from design_list-arduino.txt (separated by [labX_taskY])
and runs create_and_build for each task, outputting to iot_project/labX_taskY/
"""

import argparse
import asyncio
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def parse_tasks(filepath: str) -> dict:
    """Parse tasks from design list file.

    Args:
        filepath: Path to design_list file

    Returns:
        Dict mapping task_id (e.g., 'lab1_task1') to task description
    """
    with open(filepath, 'r') as f:
        content = f.read()

    # Split by [labX_taskY] markers
    pattern = r'\[(lab\d+_task\d+)\]'
    parts = re.split(pattern, content)

    tasks = {}
    # parts[0] is empty or content before first marker
    # then alternating: task_id, task_content, task_id, task_content, ...
    for i in range(1, len(parts), 2):
        task_id = parts[i]
        task_content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if task_content:
            tasks[task_id] = task_content

    return tasks


async def run_task(task_id: str, task_content: str, platform: str, output_base: str):
    """Run a single task.

    Args:
        task_id: Task identifier (e.g., 'lab1_task1')
        task_content: Task description
        platform: Target platform ('Arduino' or 'ESP-IDF')
        output_base: Base output directory
    """
    from dotenv import load_dotenv
    load_dotenv()

    from src.agent.config import BaseConfig
    from src.agent.graph import build_graph

    print(f"\n{'='*60}")
    print(f"🚀 Running {task_id}")
    print(f"{'='*60}")
    print(f"📝 Task: {task_content[:100]}...")

    # Write task to design.txt
    with open("design.txt", "w") as f:
        f.write(task_content)

    # Output directory for this task
    output_dir = os.path.join(output_base, task_id)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    # Set project name to output directly to target directory
    BaseConfig.DEFAULT_PROJECT_NAME = output_dir

    # Run the graph
    try:
        graph = build_graph(platform)
        result = await graph.ainvoke({"platform": platform, "design_file": "design.txt"})
        print(f"✅ {task_id} complete -> {output_dir}")

    except Exception as e:
        print(f"❌ {task_id} failed: {e}")
        import traceback
        traceback.print_exc()
    


def log_config(output_dir: str, platform: str):
    """Log config values to a YAML file in the output directory."""
    from datetime import datetime
    from src.agent.config import get_config
    from src.agent.skill_registry import ENABLED_SKILLS

    config = get_config(platform)
    log_path = os.path.join(output_dir, "config.yaml")

    with open(log_path, "w") as f:
        f.write(f"# Batch Evaluation Config\n")
        f.write(f"generated: {datetime.now().isoformat()}\n\n")
        f.write(f"platform: {platform}\n")
        f.write(f"anthropic_model: {config.ANTHROPIC_MODEL}\n")
        f.write(f"max_retries: {config.MAX_RETRIES}\n")
        f.write(f"timeout_seconds: {config.TIMEOUT_SECONDS}\n")
        f.write(f"generate_wiring_diagram: {config.GENERATE_WIRING_DIAGRAM}\n\n")
        f.write(f"enabled_skills:\n")
        for skill in ENABLED_SKILLS:
            f.write(f"  - {skill}\n")

    print(f"📝 Config logged to {log_path}")


async def main():
    parser = argparse.ArgumentParser(description="Batch evaluation for IoT agent")
    parser.add_argument(
        "--platform", "-p",
        choices=["Arduino", "ESP-IDF"],
        default="Arduino",
        help="Target platform (default: Arduino)"
    )
    parser.add_argument(
        "--input", "-i",
        default="design_list-arduino.txt",
        help="Input task list file (default: design_list-arduino.txt)"
    )
    parser.add_argument(
        "--output", "-o",
        default="iot_project",
        help="Output base directory (default: iot_project)"
    )
    parser.add_argument(
        "--tasks", "-t",
        nargs="*",
        help="Specific tasks to run (e.g., lab1_task1 lab2_task2). If not specified, runs all."
    )
    args = parser.parse_args()

    # Parse tasks
    tasks = parse_tasks(args.input)
    print(f"📋 Found {len(tasks)} tasks in {args.input}")

    # Filter tasks if specified
    if args.tasks:
        tasks = {k: v for k, v in tasks.items() if k in args.tasks}
        print(f"🎯 Running {len(tasks)} selected tasks: {list(tasks.keys())}")

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Log config values
    log_config(args.output, args.platform)

    # Run each task
    for task_id, task_content in tasks.items():
        await run_task(task_id, task_content, args.platform, args.output)

    print(f"\n{'='*60}")
    print(f"🏁 Batch evaluation complete")
    print(f"📁 Results in: {args.output}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
