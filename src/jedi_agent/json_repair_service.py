import json
import logging
import re
from json_repair import repair_json

logger = logging.getLogger(__name__)

def natural_language_to_json(text: str) -> str:
    """
    Attempts to convert natural language text to a JSON structure.
    This is a fallback mechanism for when the LLM outputs natural language instead of JSON.
    
    Args:
        text: The natural language text from the LLM.
        
    Returns:
        A JSON-formatted string that represents the content.
    """
    logger.debug(f"Attempting to convert natural language to JSON: {text[:200]}...")
    
    # Check if it looks like a project plan with steps
    step_pattern = re.compile(r'(?:Step|Phase)\s*\d+:?\s*(.*?)(?=(?:Step|Phase)\s*\d+:|$)', re.DOTALL | re.IGNORECASE)
    steps = step_pattern.findall(text)
    
    if steps:
        logger.debug(f"Found {len(steps)} steps in natural language text")
        return json.dumps({"refined_plan": {"steps": [step.strip() for step in steps]}})
    
    # Check if it looks like a list of file operations
    file_pattern = re.compile(r'(?:create|edit)\s+(?:file|directory).*?[\'"`](.*?)[\'"`]', re.DOTALL | re.IGNORECASE)
    files = file_pattern.findall(text)
    
    if files:
        logger.debug(f"Found {len(files)} file operations in natural language text")
        actions = []
        for file in files:
            actions.append({
                "action": "create_file",
                "path": file.strip(),
                "content": "# Auto-generated from natural language\n# Please edit this file with actual content"
            })
        return json.dumps({"actions": actions})
    
    # If all else fails, create a generic plan structure
    logger.debug("Creating generic JSON structure from natural language")
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    
    if paragraphs:
        return json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "plan.md",
                    "content": "# Generated Plan\n\n" + "\n\n".join(paragraphs)
                }
            ]
        })
    
    # Last resort
    return json.dumps({"actions": []})

def wrap_code_as_action(raw_output, filename_hint="main.py"):
    """
    Wraps a code block or list of code lines into a JSON create_file action.
    Args:
        raw_output: The raw output from the LLM (string or list)
        filename_hint: The default filename to use
    Returns:
        A JSON string with a single create_file action
    """
    if isinstance(raw_output, list):
        # Join list of lines into a single string
        code_content = "\n".join(str(line) for line in raw_output)
    else:
        code_content = str(raw_output)
    return json.dumps({
        "actions": [
            {
                "action": "create_file",
                "path": filename_hint,
                "content": code_content
            }
        ]
    })

# Modified to always return a dict for better error handling
def repair_and_parse_json(json_string: str) -> dict:
    """
    Attempts to repair a malformed JSON string and then parse it. Always returns a dict.

    Args:
        json_string: The potentially malformed JSON string from the LLM.

    Returns:
        A dictionary representing the parsed JSON, or an error dictionary if parsing fails.
    """
    logger.debug(f"Attempting to repair and parse JSON: {json_string[:500]}...")
    try:
        # First try direct parsing
        try:
            parsed_data = json.loads(json_string)
            logger.info("Successfully parsed JSON without repair.")
            return parsed_data
        except json.JSONDecodeError:
            logger.debug("Direct parsing failed, attempting repair...")
        
        # Attempt to repair the JSON string
        repaired_json_string = repair_json(json_string)
        logger.debug(f"Repaired JSON string: {repaired_json_string[:500]}...")
        parsed_data = json.loads(repaired_json_string)
        logger.info("Successfully repaired and parsed JSON.")
        return parsed_data
    except Exception as e:
        error_msg = f"Failed to repair or parse JSON: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Original string (first 500 chars): {json_string[:500]}...")
        # Try to convert natural language to JSON as a last resort
        try:
            logger.debug("Attempting natural language to JSON conversion as fallback...")
            nl_json = natural_language_to_json(json_string)
            parsed_data = json.loads(nl_json)
            logger.info("Successfully converted natural language to JSON.")
            return parsed_data
        except Exception as nl_e:
            logger.error(f"Natural language conversion failed: {str(nl_e)}")
            # Try to wrap raw code as a create_file action as a final fallback
            try:
                logger.debug("Attempting to wrap raw output as code file action...")
                wrapped_json = wrap_code_as_action(json_string)
                parsed_data = json.loads(wrapped_json)
                logger.info("Successfully wrapped raw output as code file action.")
                return parsed_data
            except Exception as code_wrap_e:
                logger.error(f"Wrapping raw output as code file failed: {str(code_wrap_e)}")
                return {"error": error_msg, "original_string": json_string[:500]}


# Modified to always return a dict for better error handling, similar to repair_and_parse_json
def extract_and_repair_json(raw_llm_output: str) -> dict:
    """
    Extracts a JSON string from raw LLM output and attempts to repair and parse it. Always returns a dict.

    Args:
        raw_llm_output: The raw string output from the LLM.

    Returns:
        A dictionary representing the parsed JSON, or an error dictionary if no JSON is found or parsing fails.
    """
    logger.debug(f"Attempting to extract JSON from LLM output: {raw_llm_output[:500]}")
    
    # First, try to parse the entire output directly
    try:
        parsed_data = json.loads(raw_llm_output.strip())
        logger.info("Successfully parsed entire output as JSON.")
        return parsed_data
    except json.JSONDecodeError:
        logger.debug("Direct parsing of entire output failed, trying extraction methods...")
    
    # Try to extract content from a markdown code block first (with more flexible pattern)
    try:
        code_block_patterns = [
            r'```(?:json|markdown|python|text)?\s*\n(.*?)\n```',  # Standard markdown code block
            r'```(?:json|markdown|python|text)?(.*?)```',         # Code block without newlines
            r'`{3,}(.*?)`{3,}'                                    # Any triple backtick block
        ]
        
        for pattern in code_block_patterns:
            code_block_match = re.search(pattern, raw_llm_output, re.DOTALL)
            if code_block_match:
                extracted_content = code_block_match.group(1).strip()
                logger.debug(f"Extracted content from code block: {extracted_content[:500]}...")
                result = repair_and_parse_json(extracted_content)
                if 'error' not in result:
                    return result
        
        logger.debug("No valid JSON found in code blocks, trying other patterns...")
    except re.error as e:
        error_msg = f"Regex error in code block match: {str(e)}"
        logger.error(error_msg)
    
    # If no code block with valid JSON, try to find the first complete JSON object
    try:
        json_match = re.search(r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}', raw_llm_output, re.DOTALL)
        if json_match:
            extracted_content = json_match.group(0).strip()
            logger.debug(f"Extracted JSON-like content: {extracted_content[:500]}...")
            result = repair_and_parse_json(extracted_content)
            if 'error' not in result:
                return result
            
        logger.debug("No valid JSON object found, trying array pattern...")
    except re.error as e:
        error_msg = f"Regex error in JSON object match: {str(e)}"
        logger.error(error_msg)
    
    # If no JSON object, try to find the first complete JSON array
    try:
        array_match = re.search(r'\[(?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*\]', raw_llm_output, re.DOTALL)
        if array_match:
            extracted_content = array_match.group(0).strip()
            logger.debug(f"Extracted array-like content: {extracted_content[:500]}...")
            result = repair_and_parse_json(extracted_content)
            if 'error' not in result:
                return result
            
        logger.debug("No valid JSON array found, trying natural language conversion...")
    except re.error as e:
        error_msg = f"Regex error in JSON array match: {str(e)}"
        logger.error(error_msg)
    
    # If no JSON structure found, try natural language conversion
    try:
        logger.debug("Attempting natural language to JSON conversion...")
        nl_json = natural_language_to_json(raw_llm_output)
        parsed_data = json.loads(nl_json)
        logger.info("Successfully converted natural language to JSON.")
        return parsed_data
    except Exception as nl_e:
        logger.error(f"Natural language conversion failed: {str(nl_e)}")
        # Try to wrap raw code as a create_file action as a final fallback
        try:
            logger.debug("Attempting to wrap raw output as code file action...")
            wrapped_json = wrap_code_as_action(raw_llm_output)
            parsed_data = json.loads(wrapped_json)
            logger.info("Successfully wrapped raw output as code file action.")
            return parsed_data
        except Exception as code_wrap_e:
            logger.error(f"Wrapping raw output as code file failed: {str(code_wrap_e)}")
    
    # Last resort: try to repair the entire output
    logger.debug(f"All extraction methods failed, attempting to repair entire output: {raw_llm_output[:500]}...")
    return repair_and_parse_json(raw_llm_output.strip())
