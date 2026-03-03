import os

def normalize_keys(input_dict):
    """ Recursively convert all dictionary keys to lowercase."""
    if isinstance(input_dict, dict):
        return {k.lower(): normalize_keys(v) for k, v in input_dict.items()}
    elif isinstance(input_dict, list):
        return [normalize_keys(item) for item in input_dict]
    else:
        return input_dict

def load_tool_links(tool_name, tools_dir):
    """Load tool links and return a list of links"""
    tool_file_path = os.path.join(tools_dir, f"{tool_name}.txt")
    if os.path.exists(tool_file_path):
        with open(tool_file_path, "r", encoding="utf-8") as file:
            tool_links = [line.strip() for line in file if line.strip()]
        return tool_links
    return []
