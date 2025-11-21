# Utility functions - contains helpers for: markdown parsing by headers (h1, h2, h3), section extraction with metadata, context window management, and error handling utilities

import re
from typing import Dict, Any


def parse_markdown_sections(markdown_text: str) -> Dict[str, Any]:
    """
    Parse markdown text into a hierarchical structure based on headers.
    
    Handles headers like:
    ## 1. DISPOSICIONES GENERALES
    ## 1.1 DEFINICIONES
    ## 1.2 OBJETO DE LA LICITACIÓN
    ## 2 INSTRUCCIONES GENERALES
    ## 2.1 ANTICIPO
    
    Returns a nested dictionary structure with sections and subsections.
    """
    lines = markdown_text.split('\n')
    
    # Structure to hold the parsed document
    document = {
        "title": "",
        "content": [],
        "sections": []
    }
    
    current_section = None
    current_subsection = None
    current_content = []
    
    # Regex patterns for different header levels
    # Matches: ## 1. Title, ## 1.1 Title, ## 1.1.1 Title, ## Title
    header_pattern = re.compile(r'^##\s+(\d+(?:\.\d+)*\.?)\s*(.+)$')
    simple_header_pattern = re.compile(r'^##\s+([^#\d].+)$')
    
    for line in lines:
        # Check for numbered headers (## 1. or ## 1.1 or ## 1.1.1)
        header_match = header_pattern.match(line)
        simple_match = simple_header_pattern.match(line)
        
        if header_match:
            number = header_match.group(1).rstrip('.')
            title = header_match.group(2).strip()
            
            # Determine the level based on dots in the number
            level = number.count('.') + 1
            
            if level == 1:
                # Save previous section if exists
                if current_section:
                    if current_subsection:
                        current_subsection["content"] = '\n'.join(current_content).strip()
                        current_section["subsections"].append(current_subsection)
                        current_subsection = None
                    elif current_content:
                        current_section["content"] = '\n'.join(current_content).strip()
                    document["sections"].append(current_section)
                    current_content = []
                
                # Start new main section
                current_section = {
                    "number": number,
                    "title": title,
                    "content": "",
                    "subsections": []
                }
            
            elif level >= 2:
                # Save previous subsection if exists
                if current_subsection:
                    current_subsection["content"] = '\n'.join(current_content).strip()
                    if current_section:
                        current_section["subsections"].append(current_subsection)
                    current_content = []
                
                # Start new subsection
                current_subsection = {
                    "number": number,
                    "title": title,
                    "content": ""
                }
        
        elif simple_match:
            # Handle simple headers without numbers (## TITLE)
            title = simple_match.group(1).strip()
            
            # Save previous section if exists
            if current_section:
                if current_subsection:
                    current_subsection["content"] = '\n'.join(current_content).strip()
                    current_section["subsections"].append(current_subsection)
                    current_subsection = None
                elif current_content:
                    current_section["content"] = '\n'.join(current_content).strip()
                document["sections"].append(current_section)
                current_content = []
            
            # Start new section without number
            current_section = {
                "number": "",
                "title": title,
                "content": "",
                "subsections": []
            }
        
        else:
            # Regular content line
            if not document["title"] and line.strip() and not line.startswith('#'):
                # First non-empty, non-header line could be the document title
                if not current_section and not document["content"]:
                    document["title"] = line.strip()
                    continue
            
            # Add to current content buffer
            if current_section or document["content"] is not None:
                current_content.append(line)
            else:
                # Content before any section
                document["content"].append(line)
    
    # Save the last section
    if current_section:
        if current_subsection:
            current_subsection["content"] = '\n'.join(current_content).strip()
            current_section["subsections"].append(current_subsection)
        elif current_content:
            current_section["content"] = '\n'.join(current_content).strip()
        document["sections"].append(current_section)
    
    # Convert content list to string if it exists
    if isinstance(document["content"], list):
        document["content"] = '\n'.join(document["content"]).strip()
    
    return document

# Made with Bob
