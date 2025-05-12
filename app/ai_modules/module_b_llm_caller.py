"""
LLM Caller for AI Module B (Intelligent Markdown Note Generation)
"""
import json
import re
from typing import Dict, Any, List
import uuid # For potential noteId placeholder generation if needed, though DB will create final

import google.generativeai as genai

from app.core.config import Settings
from app.ai_modules.prompts_module_b import SYSTEM_PROMPT_B_V1_0

async def invoke_module_b_llm(module_a1_output: Dict[str, Any], module_a2_output: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Invokes the Gemini LLM for Module B to generate intelligent Markdown notes.

    Args:
        module_a1_output: The dictionary result from the invoke_module_a1_llm call.
        module_a2_output: The dictionary result from the invoke_module_a2_llm call.
        settings: The application settings instance.

    Returns:
        A dictionary containing the LLM's structured output for Module B.

    Raises:
        ValueError: If the LLM response is invalid or missing required fields.
        Exception: For other LLM API call failures.
    """
    video_id_from_a1 = module_a1_output.get('videoId')
    print(f"Attempting to call Gemini for Module B. Input videoId: {video_id_from_a1}")

    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY.get_secret_value())
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Prepare the user message for Module B
        user_message_input_data = {
            "moduleA1Output": module_a1_output,
            "moduleA2Output": module_a2_output
        }

        user_message_content = f"""
Please process the following structured data, which includes the full transcript context from Module A.1 and the extracted key information from Module A.2. Use this data to generate an intelligent Markdown study note and its associated metadata, adhering strictly to your system prompt instructions (SYSTEM_PROMPT_B_V1_0).

Input Data:
```json
{json.dumps(user_message_input_data, ensure_ascii=False, indent=2)}
```

Ensure your output is a single, valid JSON object as specified in your system prompt for Module B. Remember to generate a placeholder for `noteId` like "[NOTE_ID]" or a UUID-like string, and a placeholder for `generationTimestamp` like "[SYSTEM_GENERATED_TIMESTAMP_YYYY-MM-DDTHH:MM:SSZ]".
The videoId in your output MUST be "{video_id_from_a1}".
"""
        
        print(f"Module B LLM User Message prepared. Length: {len(user_message_content)} chars.")
        # print(f"Module B LLM User Message snippet: {user_message_content[:500]}") # Uncomment for debugging

        response = await model.generate_content_async(
            [SYSTEM_PROMPT_B_V1_0, user_message_content],
            generation_config=genai.types.GenerationConfig(temperature=0.4)
        )

        print("LLM B call successful. Response received.")
        
        response_text = response.text
        # Strip markdown ```json ... ``` wrapper if present
        match = re.search(r"```json\n(.*)\n```", response_text, re.DOTALL)
        if match:
            cleaned_response_text = match.group(1).strip()
        else:
            # Handle cases where LLM might forget the json wrapper but still outputs valid JSON string
            cleaned_response_text = response_text.strip()
            if not (cleaned_response_text.startswith('{') and cleaned_response_text.endswith('}')):
                 # Or if it outputs just the markdown content directly without JSON
                if "noteMarkdownContent" not in cleaned_response_text and len(cleaned_response_text) > 100: # Heuristic
                    print("Warning: LLM B might have outputted markdown directly. Attempting to wrap as JSON.")
                    # This is a fallback, LLM should ideally always return JSON
                    # For now, we'll let it fail parsing if this wrapping is incorrect.
                    # A more robust solution would be to ask for re-generation or have a specific parser.
                    # For MVP, we rely on prompt adherence. If parsing fails, it will be caught.
                    pass # Let JSON parsing handle it, or fail.

        
        parsed_output = json.loads(cleaned_response_text)
        print("LLM B response parsed successfully.")

        # Basic Validation
        if not isinstance(parsed_output, dict):
            raise ValueError("LLM B response is not a JSON object.")
        
        # Validate videoId
        if parsed_output.get("videoId") != video_id_from_a1:
            print(f"Warning: LLM B videoId '{parsed_output.get('videoId')}' differs from input '{video_id_from_a1}'. Overwriting.")
            parsed_output["videoId"] = video_id_from_a1

        # Validate essential fields
        required_fields = {
            "noteId": str, # Placeholder is fine, type is str
            "noteMarkdownContent": str,
            "estimatedReadingTimeSeconds": int,
            "keyConceptsMentioned": list,
            "summaryOfNote": str
        }
        for field, field_type in required_fields.items():
            if field not in parsed_output:
                raise ValueError(f"LLM B response missing required field: '{field}'. Output: {json.dumps(parsed_output, indent=2)}")
            if not isinstance(parsed_output[field], field_type):
                # Special handling for list of strings for keyConceptsMentioned
                if field == "keyConceptsMentioned" and isinstance(parsed_output[field], list):
                    if not all(isinstance(item, str) for item in parsed_output[field]):
                        raise ValueError(f"LLM B response field '{field}' has incorrect item types in list. Expected list of str. Got: {parsed_output[field]}")
                else:
                    raise ValueError(f"LLM B response field '{field}' has incorrect type. Expected {field_type}. Got {type(parsed_output[field])}. Output: {json.dumps(parsed_output, indent=2)}")

        # generationTimestamp is handled by orchestrator if placeholder

        print(f"LLM B output validated. Note summary: {parsed_output['summaryOfNote'][:100]}...")
        return parsed_output

    except json.JSONDecodeError as e:
        print(f"Error: LLM B JSON parsing error: {e}")
        print(f"LLM B Raw problematic response text: {response_text if 'response_text' in locals() else 'Response text not available'}")
        raise ValueError(f"LLM B failed to produce valid JSON: {e}") from e
    except ValueError as ve: # Catch validation errors
        print(f"Error: LLM B Validation Error: {ve}")
        raise
    except Exception as e:
        print(f"Error: LLM B API call failed: {e}")
        # Consider logging more details for debugging if needed
        raise Exception(f"LLM B API call failed: {e}") from e 