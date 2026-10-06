#!/usr/bin/env python3
import os
import shutil

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
TEXT_EXTS = {".md", ".py", ".html", ".json", ".yaml", ".yml", ".txt", ".sh", ".toml", ""}

REPLACEMENTS = [
    ("https://github.com/anuroopanand7/buildingbees", "https://github.com/anuroopanand7/buildingbees"),
    ("anuroopanand7/buildingbees", "anuroopanand7/buildingbees"),
    ("BuildingBees: The Super Intelligent Product Management Hive", "BuildingBees: The Super Intelligent Product Management Hive"),
    ("BuildingBees — Super Intelligent Product Management Hive", "BuildingBees — Super Intelligent Product Management Hive"),
    ("BuildingBees", "BuildingBees"),
    ("buildingbees", "buildingbees"),
    ("BuildingBees", "BuildingBees"),
    ("BuildingBees: The Agentic Multi-Agent Product Hive", "BuildingBees: The Agentic Multi-Agent Product Hive"),
    ("BuildingBees", "BuildingBees"),
    ("buildingbees-mcp", "buildingbees-mcp"),
    ("buildingbees", "buildingbees"),
    ("test_buildingbees.py", "test_buildingbees.py"),
]

# 1. Text replacement in all files
print("--- Updating file contents ---")
for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
    dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
    for fname in filenames:
        ext = os.path.splitext(fname)[1]
        base = fname
        if ext in TEXT_EXTS or base in {"Dockerfile", "cloudbuild.yaml", "requirements.txt", ".gitignore"}:
            filepath = os.path.join(dirpath, fname)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                new_content = content
                for old, new in REPLACEMENTS:
                    new_content = new_content.replace(old, new)

                if new_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"Updated content: {os.path.relpath(filepath, ROOT_DIR)}")
            except Exception as e:
                print(f"Error updating {filepath}: {e}")

# 2. File renames
print("\n--- Renaming files ---")
FILE_RENAMES = [
    ("tests/test_buildingbees.py", "tests/test_buildingbees.py"),
    ("second_brain/10_BuildingBees_Master_PRD.md", "second_brain/10_BuildingBees_Master_PRD.md"),
    ("second_brain/11_BuildingBees_Hive_Requirements_and_Architecture.md", "second_brain/11_BuildingBees_Hive_Requirements_and_Architecture.md"),
]

for old_rel, new_rel in FILE_RENAMES:
    old_path = os.path.join(ROOT_DIR, old_rel)
    new_path = os.path.join(ROOT_DIR, new_rel)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        print(f"Renamed file: {old_rel} -> {new_rel}")
    else:
        print(f"File not found (already renamed?): {old_rel}")

print("\n--- Project rename completed! ---")
