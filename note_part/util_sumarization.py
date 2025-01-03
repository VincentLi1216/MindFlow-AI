import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(current_dir)

import os
import json
from llm import OpenAILLM
from pydantic import BaseModel, Field

from common import get_hash, list_md_files

llm = OpenAILLM()

template = """Generate a concise summary based on the provided document content. The summary should be limited to a single paragraph and must be written in the same language as the original document.

# Steps

1. Read and understand the full content of the document provided.
2. Identify the main points, arguments, or essential information in the document.
3. Synthesize these key points into a single coherent paragraph, ensuring the information flows logically.
4. Maintain the language used in the original document for consistency.

# Output Format

- A single paragraph summarizing the document.
- Maintain the same language as the original document for the summary. 

# Notes

- Focus on clarity, ensuring that the most relevant information is captured succinctly.
- Avoid adding your own opinions or interpretations beyond what is presented in the document.

# Here is the document content:

{document}
"""

class SummarizeResponse(BaseModel):
    text: str = Field(description="The summarized text.")
    
llm.build(template=template, schema=SummarizeResponse)


def _summarize(file_path: str) -> str:
    """
    Generate a concise summary based on the provided document content.
    
    :param file_path: The file path of the note file.
    :return: The summarized text.
    """
    content =  f"""
# {file_path.split('/')[-1].replace('.md', '')}
---
{open(file_path, 'r').read()}
"""
    response = llm.invoke({"document": content})
    
    return response.text


def summarize_file(root_path, file_path):
    """
    Generate a concise summary based on the provided document content.
    
    :param root_path: The root directory containing the Markdown files.
    :param file_path: The relative path of the Markdown file to summarize.
    :return: The summarized text.
    """
    summary = _summarize(os.path.join(root_path, file_path))
    
    with open(os.path.join(root_path, '.mindflow', 'summary.json'), 'r') as f:
        summaries = json.load(f)
        
    summaries['data'][get_hash(file_path)] = {
        'path': file_path,
        'text': summary
    }
    
    with open(os.path.join(root_path, '.mindflow', 'summary.json'), 'w') as f:
        f.write(json.dumps(summaries))

    return summary


def batch_summarize(root_path):
    """
    Batch process all the Markdown files in the provided directory and generate summaries for each file.
    
    :param root_path: The root directory containing the Markdown files.
    :return: A message indicating the completion of the summarization process.
    """
    if 'summary.json' not in os.listdir(os.path.join(root_path, '.mindflow')):
        print("Creating the summary.json file...")
        summaries = {'root': root_path, 'data': {}}
        with open(os.path.join(root_path, '.mindflow', 'summary.json'), 'w') as f:
            f.write(json.dumps(summaries))
    else:
        with open(os.path.join(root_path, '.mindflow', 'summary.json'), 'r') as f:
            summaries = json.load(f)
    
    md_files = list_md_files(root_path)
    
    for file_path in md_files:
        text = _summarize(file_path['absolute_path'])
        summaries['data'][get_hash(file_path['relative_path'])] = {
                'path': file_path['relative_path'],
                'text': text
            }
        
    with open(os.path.join(root_path, '.mindflow', 'summary.json'), 'w') as f:
        f.write(json.dumps(summaries))
    
    return "Process completed successfully."


if __name__ == "__main__":
    root_path = "/Users/USER/Desktop/Side_project/MindFlow-AI/note_part/data/TestingNote"
    file_path = "paper/Large Language Model based Multi-Agents- A Survey of Progress and Challenges.md"
    
    print(_summarize(root_path, file_path))