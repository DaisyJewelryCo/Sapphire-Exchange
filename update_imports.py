"""
Script to update import statements from 'mock_servers' to 'mock_server'.
Run this script from the project root directory.
"""
import os
import re

def update_file(file_path):
    """Update import statements in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace all occurrences of 'mock_servers' with 'mock_server' in import statements
        updated_content = re.sub(
            r'from\s+mock_servers\s+import',
            'from mock_server import',
            content
        )
        
        # Only write if changes were made
        if updated_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"Updated: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to update all Python files in the project."""
    # Get all Python files in the project
    python_files = []
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and not file.startswith('venv') and not file.startswith('.'):
                python_files.append(os.path.join(root, file))
    
    # Update each file
    updated_count = 0
    for file_path in python_files:
        if update_file(file_path):
            updated_count += 1
    
    print(f"\nUpdate complete. {updated_count} files were updated.")

if __name__ == "__main__":
    main()
