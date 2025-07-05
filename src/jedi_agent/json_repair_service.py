import json
import logging
from json_repair import repair_json

logger = logging.getLogger(__name__)

def repair_and_parse_json(json_string: str) -> dict | None:
    """
    Attempts to repair a malformed JSON string and then parse it.

    Args:
        json_string: The potentially malformed JSON string from the LLM.

    Returns:
        A dictionary representing the parsed JSON, or None if repair and parsing fail.
    """
    logger.debug(f"Attempting to repair and parse JSON: {json_string[:500]}...")
    try:
        # Attempt to repair the JSON string
        repaired_json_string = repair_json(json_string)
        logger.debug(f"Repaired JSON string: {repaired_json_string[:500]}...")

        # Attempt to parse the repaired JSON string
        parsed_data = json.loads(repaired_json_string)
        logger.info("Successfully repaired and parsed JSON.")
        return parsed_data
    except Exception as e:
        logger.error(f"Failed to repair or parse JSON: {e}")
        logger.error(f"Original string (first 500 chars): {json_string[:500]}...")
        return None


def extract_and_repair_json(raw_llm_output: str) -> dict | None:
    """
    Extracts a JSON string from raw LLM output and then attempts to repair and parse it.

    Args:
        raw_llm_output: The raw string output from the LLM.

    Returns:
        A dictionary representing the parsed JSON, or None if extraction, repair, or parsing fail.
    """
    # First, try to extract content from a markdown code block (e.g., ```json ... ```)
    import re
    code_block_match = re.search(r'```(?:json|markdown|python|text)?\s*\n(.*?)\n```', raw_llm_output, re.DOTALL)
    if code_block_match:
        extracted_content = code_block_match.group(1).strip()
        logger.debug(f"Extracted content from code block: {extracted_content[:500]}...")
    else:
        # If no code block, try to find the first '{' and last '}'
        # If no code block, assume the entire output should be JSON
        # This makes it stricter, forcing the LLM to output only JSON if not in a code block
        extracted_content = raw_llm_output.strip()
        logger.debug(f"No code block found, treating entire output as JSON: {extracted_content[:500]}...")

    return repair_and_parse_json(extracted_content)
