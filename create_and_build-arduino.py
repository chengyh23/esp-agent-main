#!/usr/bin/env python3
"""Example script to create and build an Arduino project using the agent."""

import asyncio
import os
import sys
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent_arduino.graph import graph

async def main():
    # Load environment variables from .env file if it exists
    from dotenv import load_dotenv
    load_dotenv()

    # Import and validate configuration
    from src.agent_arduino.config import config

    if config.VERBOSE_LOGGING:
        config.print_config()

    # Check if ANTHROPIC_API_KEY is set
    if not config.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not found!")
        print("Please set your Anthropic API key in the .env file or environment variable.")
        return

    # Clean up existing project directory
    project_dir = config.DEFAULT_PROJECT_NAME
    if os.path.exists(project_dir):
        print(f"🧹 Removing existing project directory: {project_dir}")
        shutil.rmtree(project_dir)
    
    # Create project from design file
    design_file = config.DESIGN_FILE_PATH  # Use config for design file path
    
    print("🤖 Arduino Project Creator Agent")
    print("=" * 50)
    print(f"📄 Reading design from: {design_file}")
    
    # Read and display the design
    with open(design_file, 'r') as f:
        design_content = f.read().strip()
    print(f"📝 Design: {design_content}")
    print()
    
    print("🧠 Agent is thinking and generating code...")
    print("-" * 50)
    
    result = await graph.ainvoke({"design_file": design_file})
    
    print("✅ Project created successfully!")
    print(f"📁 Location: ./{result['message'].split('in ./')[1]}")
    print()
    
    # Show the generated files
    project_dir = config.DEFAULT_PROJECT_NAME
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
        
        # Show the generated code (Arduino uses .ino files)
        ino_path = os.path.join(project_dir, f"{project_dir}.ino")
        if os.path.exists(ino_path):
            print("💻 Generated Arduino Code (.ino):")
            print("-" * 50)
            with open(ino_path, 'r') as f:
                code = f.read()
            print(code)
            print("-" * 50)
        
        # Show wiring instructions if available
        wiring_path = os.path.join(project_dir, "WIRING.md")
        if os.path.exists(wiring_path):
            print("🔌 Wiring Instructions:")
            print("-" * 50)
            with open(wiring_path, 'r') as f:
                wiring = f.read()
            print(wiring)
            print("-" * 50)
        
        # Show README if available
        readme_path = os.path.join(project_dir, "README.md")
        if os.path.exists(readme_path):
            print("📖 README:")
            print("-" * 50)
            with open(readme_path, 'r') as f:
                readme = f.read()
            print(readme)
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())