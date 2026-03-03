# Tool Knowledge Base Usage Guide

## Overview

The `doc/tool/` folder stores tool-related knowledge documents in txt format. These documents are loaded into the vector database together with the existing JSON format knowledge base.

## File Format

- **File extension**: `.txt`
- **Encoding**: UTF-8
- **Content format**: Plain text, supports newlines and special characters

## File Naming Rules

- Use descriptive filenames, e.g. `plink_tool.txt`, `admixture_tool.txt`
- Filename (without extension) is stored as `source` field in metadata
- Avoid special characters and spaces

## Metadata Structure

Each txt file generates the following metadata when loaded:

```json
{
  "source": "filename (without extension)",
  "file_type": "txt",
  "file_path": "full file path"
}
```

## Usage

1. Save tool-related knowledge documents as `.txt` files
2. Place them in the `doc/tool/` folder
3. Restart the application or reload the knowledge base
4. Documents will be automatically loaded into the vector database

## Example Files

- `plink_tool.txt`: PLINK tool usage guide
- `admixture_tool.txt`: ADMIXTURE tool usage guide

## Notes

1. File content cannot be empty; empty files are skipped
2. Supports both Chinese and English content
3. Markdown format is recommended for better readability
4. Keep file size reasonable (< 1MB)

## Compatibility with JSON Format

- Existing `Task_Konwledge.json` file remains valid
- txt and JSON files are loaded into the knowledge base simultaneously
- Both formats can be used together
