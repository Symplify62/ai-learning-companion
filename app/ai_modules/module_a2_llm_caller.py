"""
LLM Caller for AI Module A.2 (Core Content Deep Understanding & Key Information Extraction)
"""
import json
import re
from typing import Dict, Any, List

import google.generativeai as genai

from app.core.config import Settings
from app.ai_modules.prompts_module_a2 import SYSTEM_PROMPT_A2_V1_1

async def invoke_module_a2_llm(module_a1_llm_output: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Invokes the Gemini LLM for Module A.2 to perform deep content analysis and extract key information.

    Args:
        module_a1_llm_output: The dictionary result from the invoke_module_a1_llm call.
        settings: The application settings instance.

    Returns:
        A dictionary containing the LLM's structured output for Module A.2.

    Raises:
        ValueError: If the LLM response is invalid or missing required fields.
        Exception: For other LLM API call failures.
    """
    print(f"Attempting to call Gemini for Module A.2. Input videoId: {module_a1_llm_output.get('videoId')}")

    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY.get_secret_value())
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Prepare the user message
        # We only need to pass what's relevant for A2 as per its prompt (A1's output structure)
        user_message_input_data = {
            "videoId": module_a1_llm_output.get("videoId"),
            "videoTitle": module_a1_llm_output.get("videoTitle"),
            "videoDescription": module_a1_llm_output.get("videoDescription"),
            "sourceDescription": module_a1_llm_output.get("sourceDescription"),
            "processingTimestamp": module_a1_llm_output.get("processingTimestamp"), # Pass A1's timestamp
            "totalDurationSeconds": module_a1_llm_output.get("totalDurationSeconds"),
            "transcriptSegments": module_a1_llm_output.get("transcriptSegments", [])
        }

        user_message_content = f"""
        Please process the following structured transcript data (output from Module A.1) according to your instructions as the Academic Content Analyst and Information Architect AI. Your goal is to perform deep content analysis, semantic aggregation, and extract the 9 specified types of key information.

        Input Data from Module A.1:
        ```json
        {json.dumps(user_message_input_data, ensure_ascii=False, indent=2)}
        ```

        Ensure your output is a single, valid JSON object adhering to the schema specified in your system prompt.
        """
        
        print(f"Module A.2 LLM User Message prepared. Length: {len(user_message_content)} chars. First 200 chars: {user_message_content[:200]}")

        response = await model.generate_content_async(
            [SYSTEM_PROMPT_A2_V1_1, user_message_content],
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )

        print("LLM A.2 call successful. Response received.")
        
        response_text = response.text
        # Strip markdown ```json ... ``` wrapper if present
        match = re.search(r"```json\n(.*)\n```", response_text, re.DOTALL)
        if match:
            cleaned_response_text = match.group(1).strip()
        else:
            cleaned_response_text = response_text.strip()
        
        parsed_output = json.loads(cleaned_response_text)
        print("LLM A.2 response parsed successfully.")

        # Basic Validation
        if not isinstance(parsed_output, dict):
            raise ValueError("LLM A.2 response is not a JSON object.")
        
        if "videoId" not in parsed_output or parsed_output["videoId"] != module_a1_llm_output.get("videoId"):
            # Allow A.2 to use A.1's videoId if it doesn't produce one, or if it's different, log warning & use A.1's.
            # This is slightly different from A.1's handling as A.2 is directly passed A.1's output.
            print(f"Warning: LLM A.2 videoId '{parsed_output.get('videoId')}' differs or missing. Using A.1 videoId: {module_a1_llm_output.get('videoId')}")
            parsed_output["videoId"] = module_a1_llm_output.get("videoId")

        if "extractedKeyInformation" not in parsed_output or not isinstance(parsed_output["extractedKeyInformation"], list):
            print(f"Error: LLM A.2 response missing 'extractedKeyInformation' list or it's not a list. Output: {parsed_output}")
            raise ValueError("LLM A.2 response missing 'extractedKeyInformation' list or it's not a list.")

        # Placeholder for processingTimestamp as per A.2 prompt
        if parsed_output.get("processingTimestamp") == "[SYSTEM_GENERATED_TIMESTAMP_YYYY-MM-DDTHH:MM:SSZ]":
            # We might want to use a real timestamp here, but for now, let's see what A.2 returns
            # and decide if we overwrite it in orchestration.py like we did for A.1.
            # For now, keeping it as is from LLM if it's the placeholder.
            pass 
        elif "processingTimestamp" not in parsed_output:
             print(f"Warning: LLM A.2 response missing 'processingTimestamp'. This is acceptable if not required downstream from A.2 directly.")

        print(f"LLM A.2 output validated. Items found: {len(parsed_output['extractedKeyInformation'])}")
        return parsed_output

    except json.JSONDecodeError as e:
        print(f"Error: LLM A.2 JSON parsing error: {e}")
        print(f"LLM A.2 Raw problematic response text: {response_text if 'response_text' in locals() else 'Response text not available'}")
        raise ValueError(f"LLM A.2 failed to produce valid JSON: {e}") from e
    except ValueError as ve:
        print(f"Error: LLM A.2 Validation Error: {ve}")
        raise
    except Exception as e:
        print(f"Error: LLM A.2 API call failed: {e}")
        # Consider logging the full `module_a1_llm_output` or `user_message_content` if error is persistent and hard to debug
        # Be mindful of log size and sensitive data.
        raise Exception(f"LLM A.2 API call failed: {e}") from e 