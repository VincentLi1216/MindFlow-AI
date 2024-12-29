import os
import re
import json
from transformers import pipeline
from llm import OpenAILLM
from pydantic import BaseModel, Field
import hashlib

llm = OpenAILLM()

hypothesis_template = "This text is about {}"
zeroshot_classifier = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-large-zeroshot-v2.0")  # change the model identifier here

template = """Generate 5 to 10 relevant tags for categorizing the provided document content.

- Ensure the tags are specific and accurately reflect the main topics or key concepts discussed in the content.
- Avoid duplicating any existing tags. 
Here are the existing tags: {tags}.
- Use concise terms for each tag, ideally limiting each to no more than 3 words.
- Arrange the generated tags in descending order of relevance, with the most relevant tags listed first.

# Steps

1. Read and analyze the provided document content thoroughly to identify the main topics and key concepts.
2. Based on the analysis, brainstorm potential tags that capture these key ideas.
3. Cross-check each potential tag against the list of existing tags and eliminate duplicates.
4. Rank the potential tags by their relevance to the document content.
5. Select the top 5 to 10 relevant tags.
6. Ensure that each tag is concise, consisting of no more than 3 words.

# Notes

- Focus on specificity and conciseness for the tags.
- Consider the primary and secondary topics, as well as any specialized terms, discussed in the document.

# Document Content
{document}
"""

class RelativeTag(BaseModel):
    tags: list[str] = Field(..., description="List of tags generated based on the content of the document.")
    
llm.build(template=template, schema=RelativeTag)

def tag_template_matching(text: str, remove: bool = False) -> tuple[bool, str]:
    pattern = r'^---\ntags:\n.*\n---'

    if re.match(pattern, text, re.DOTALL):
        if remove:
            updated_text = re.sub(pattern, '', text, flags=re.DOTALL)
            return True, updated_text.strip()
        return True, text
    else:
        return False, text

def get_hash(input_string: str, algorithm: str = 'sha256') -> str:
    hash_object = hashlib.new(algorithm)
    hash_object.update(input_string.encode('utf-8'))
    return hash_object.hexdigest()


def classify_text(text: str, classes: list) -> dict:
    response = llm.invoke({
        "document": text,
        "tags": classes
    })
    return response.tags


def pick_existing_classes(text: str, classes_verbalized: list) -> list:
    """
    Pick the classes that are most likely to be present in the text.
    
    :param text: The input text to be classified.
    :param classes: The list of classes to choose from.
    :return: The list of classes most likely to be present in the text.
    """
    if len(classes_verbalized) == 0:
        return []
    output = zeroshot_classifier(text, classes_verbalized, hypothesis_template=hypothesis_template, multi_label=False)
    return output["labels"]


def tag(root_path, file_path):
    """
    Tag the specified Markdown file with relevant classes based on its content.
    
    :param root_path: The root directory containing the Markdown files.
    :param file_path: The relative path of the Markdown file to be tagged.
    :return: A message indicating the completion of the tagging process.
    """
    if 'tags.json' not in os.listdir(os.path.join(root_path, '.mindflow')):
        print("Creating the tags.json file...")
        tags = {'root': root_path, 'file': [], 'tags': [], 'data': {}}
        with open(os.path.join(root_path, '.mindflow', 'tags.json'), 'w') as f:
            f.write(json.dumps(tags))
    else:
        with open(os.path.join(root_path, '.mindflow', 'tags.json'), 'r') as f:
            tags = json.load(f)
    
    if file_path not in tags['file']:
        tags['file'].append(file_path)
    
    content = open(os.path.join(root_path, file_path), 'r').read()
    content = tag_template_matching(content, True)[1]
    
    labels = pick_existing_classes(content, tags['tags'])
    results = classify_text(content, labels)
    labels = list(set(results + labels))
    
    tag_template = """---\ntags:\n{tags}---"""
    
    string_tags = ""
    for label in labels:
        string_tags += f"  - {label}\n"
    
    content = f"{tag_template.format(tags=string_tags)}\n{content}"

    with open(os.path.join(root_path, file_path), 'w') as f:
        f.write(content)
    
    tags['data'][get_hash(file_path)] = {
        'file': file_path,
        'tags': labels
    }
    
    for label in labels:
        if label not in tags['tags']:
            tags['tags'].append(label)
    
    with open(os.path.join(root_path, '.mindflow', 'tags.json'), 'w') as f:
        f.write(json.dumps(tags))
    
    return "Tagging process completed successfully."

if __name__ == "__main__":
    root_path = "/Users/USER/Desktop/Side_project/MindFlow-AI/note_part/data/TestingNote"
    file_path = "paper/Large Language Model based Multi-Agents- A Survey of Progress and Challenges.md"
    
    print(tag(root_path, file_path))