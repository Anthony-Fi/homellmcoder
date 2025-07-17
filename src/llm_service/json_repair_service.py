import json
import logging
import re

# No external repair_json dependency; pure Python fallback

def wrap_code_as_action(raw_output, filename_hint="plan.md"):
    logging.debug(f"Wrapping raw output as create_file action for {filename_hint}. Raw: {repr(raw_output)[:500]}")
    if isinstance(raw_output, list):
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

def repair_and_parse_json(json_string: str) -> dict:
    logging.debug(f"[repair_and_parse_json] Attempting to repair: {repr(json_string)[:500]}")
    try:
        parsed_data = json.loads(json_string)
        logging.info("[repair_and_parse_json] Successfully parsed JSON without repair.")
        return parsed_data
    except Exception as e:
        logging.warning(f"[repair_and_parse_json] Direct parse failed: {e}")
        # fallback: try to extract JSON object
        match = re.search(r'\{(?:[^{}]|\{[^{}]*\})*\}', json_string, re.DOTALL)
        if match:
            logging.debug("[repair_and_parse_json] Found JSON object via regex extract.")
            try:
                return json.loads(match.group(0))
            except Exception as e2:
                logging.warning(f"[repair_and_parse_json] Regex parse failed: {e2}")
        # fallback: wrap as file action
        logging.error(f"[repair_and_parse_json] All repair attempts failed. Wrapping as create_file action.")
        return json.loads(wrap_code_as_action(json_string))

def extract_and_repair_json(raw_llm_output: str) -> dict:
    logging.debug(f"[extract_and_repair_json] Raw LLM output: {repr(raw_llm_output)[:1000]}")
    try:
        parsed = json.loads(raw_llm_output.strip())
        logging.info("[extract_and_repair_json] Successfully parsed raw output as JSON.")
        return parsed
    except Exception as e:
        logging.warning(f"[extract_and_repair_json] Direct parse failed: {e}")
        # Try extracting from code block
        match = re.search(r'```(?:json)?\s*\n(.*?)\n```', raw_llm_output, re.DOTALL)
        if match:
            code_block = match.group(1).strip()
            logging.debug(f"[extract_and_repair_json] Found code block: {repr(code_block)[:500]}")
            try:
                parsed = json.loads(code_block)
                logging.info("[extract_and_repair_json] Successfully parsed code block as JSON.")
                return parsed
            except Exception as e2:
                logging.warning(f"[extract_and_repair_json] Code block parse failed: {e2}")
        # fallback: repair
        logging.error(f"[extract_and_repair_json] All parse attempts failed, calling repair_and_parse_json.")
        return repair_and_parse_json(raw_llm_output)
