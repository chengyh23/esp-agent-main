#!/usr/bin/env python3
"""Script to create and build IoT projects (Arduino or ESP-IDF) using the agent."""

import argparse
import asyncio
import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent_arduino.graph import build_graph


async def main():
    parser = argparse.ArgumentParser(description="IoT Project Creator Agent")
    parser.add_argument(
        "--platform", "-p",
        choices=["Arduino", "ESP-IDF"],
        default=os.getenv("PLATFORM", "Arduino"),
        help="Target platform (default: Arduino)"
    )
    args = parser.parse_args()
    platform = args.platform

    from dotenv import load_dotenv
    load_dotenv()

    from src.agent_arduino.config import get_config
    config = get_config(platform)

    if config.VERBOSE_LOGGING:
        config.print_config()

    if not config.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not found!")
        print("Please set your Anthropic API key in the .env file or environment variable.")
        return

    # Clean up existing project directory
    project_dir = config.DEFAULT_PROJECT_NAME
    if os.path.exists(project_dir):
        print(f"🧹 Removing existing project directory: {project_dir}")
        shutil.rmtree(project_dir)

    design_file = config.DESIGN_FILE_PATH

    print(f"🤖 IoT Project Creator Agent ({platform})")
    print("=" * 50)
    print(f"📄 Reading design from: {design_file}")

    with open(design_file, 'r') as f:
        design_content = f.read().strip()
    print(f"📝 Design: {design_content}")
    print()

    print("🧠 Agent is thinking and generating code...")
    print("-" * 50)

    graph = build_graph(platform)
    result = await graph.ainvoke({"platform": platform, "design_file": design_file})

    print("✅ Project created successfully!")
    print(f"📁 Location: ./{result['message'].split('in ./')[1]}")
    print()

    # Show the generated files
    if os.path.exists(project_dir):
        print("📋 Generated files:")
        for root, dirs, files in os.walk(project_dir):
            level = root.replace(project_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}📁 {os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}📄 {file}")
        print()
        
        # # Show the generated code (Arduino uses .ino files)
        # ino_path = os.path.join(project_dir, f"{project_dir}.ino")
        # if os.path.exists(ino_path):
        #     print("💻 Generated Arduino Code (.ino):")
        #     print("-" * 50)
        #     with open(ino_path, 'r') as f:
        #         code = f.read()
        #     print(code)
        #     print("-" * 50)

        # Show wiring instructions if available
        wiring_path = os.path.join(project_dir, "WIRING.md")
        if os.path.exists(wiring_path):
            print("🔌 Wiring Instructions:")
            print("-" * 50)
            with open(wiring_path, 'r') as f:
                print(f.read())
            print("-" * 50)

        # Show README if available
        readme_path = os.path.join(project_dir, "README.md")
        if os.path.exists(readme_path):
            print("📖 README:")
            print("-" * 50)
            with open(readme_path, 'r') as f:
                print(f.read())
            print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
