"""
LLM Caller for AI Module A.2 (Plain Text Preprocessing)
"""
import json
import re
from typing import Dict, Any

import google.generativeai as genai

from app.core.config import Settings
from .prompts_module_a2_text_preprocessing import PROMPT_SYSTEM_MODULE_A2_TEXT_PREPROCESSING_V1_0

async def invoke_module_a2_text_preprocessing_llm(plain_text_input: str, settings: Settings) -> str:
    """
    Invokes the Gemini LLM for Module A.2 (Plain Text Preprocessing).

    Args:
        plain_text_input: The plain text string submitted by the user.
        settings: The application settings instance.

    Returns:
        A string containing the processed plain text.

    Raises:
        ValueError: If the LLM response is invalid or missing the required field.
        Exception: For other LLM API call failures.
    """
    print(f"Attempting to call Gemini for Module A.2 Text Preprocessing. Input length: {len(plain_text_input)}")

    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY.get_secret_value())
        model = genai.GenerativeModel('gemini-1.5-flash') # Or your preferred model

        user_message_input_data = {
            "plain_text_input": plain_text_input
        }

        user_message_content = f"""
Please process the following plain text input. Your goal is to perform light cleaning and ensure it's well-formatted for downstream note generation, adhering strictly to your system prompt instructions (PROMPT_SYSTEM_MODULE_A2_TEXT_PREPROCESSING_V1_0).

Input Data:
```json
{json.dumps(user_message_input_data, ensure_ascii=False, indent=2)}
```

Ensure your output is a single, valid JSON object containing the "processed_plain_text" field as specified in your system prompt.
"""
        
        print(f"Module A.2 Text Preprocessing LLM User Message prepared. Length: {len(user_message_content)} chars.")

        response = await model.generate_content_async(
            [PROMPT_SYSTEM_MODULE_A2_TEXT_PREPROCESSING_V1_0, user_message_content],
            generation_config=genai.types.GenerationConfig(temperature=0.2) # Low temperature for more deterministic cleaning
        )

        print("LLM A.2 Text Preprocessing call successful. Response received.")
        
        response_text = response.text
        match = re.search(r"```json\n(.*)\n```", response_text, re.DOTALL)
        if match:
            cleaned_response_text = match.group(1).strip()
        else:
            cleaned_response_text = response_text.strip()
            if not (cleaned_response_text.startswith('{') and cleaned_response_text.endswith('}')):
                 print("Warning: LLM A.2 Text Preprocessing might have outputted text directly. Attempting to wrap as JSON if it's the content.")
                 # This is a fallback; ideally, the LLM adheres to the JSON output format.
                 # If it's just the text, we might need to wrap it or handle it as an error.
                 # For now, let parsing fail if it's not proper JSON.
                 pass


        parsed_output = json.loads(cleaned_response_text)
        print("LLM A.2 Text Preprocessing response parsed successfully.")

        if not isinstance(parsed_output, dict) or "processed_plain_text" not in parsed_output:
            raise ValueError("LLM A.2 Text Preprocessing response is not a valid JSON object or missing 'processed_plain_text' field.")
        
        if not isinstance(parsed_output["processed_plain_text"], str):
             raise ValueError("LLM A.2 Text Preprocessing 'processed_plain_text' field is not a string.")

        print(f"LLM A.2 Text Preprocessing output validated. Processed text length: {len(parsed_output['processed_plain_text'])}")
        return parsed_output["processed_plain_text"]

    except json.JSONDecodeError as e:
        print(f"Error: LLM A.2 Text Preprocessing JSON parsing error: {e}")
        print(f"LLM A.2 Raw problematic response text: {response_text if 'response_text' in locals() else 'Response text not available'}")
        raise ValueError(f"LLM A.2 Text Preprocessing failed to produce valid JSON: {e}") from e
    except ValueError as ve:
        print(f"Error: LLM A.2 Text Preprocessing Validation Error: {ve}")
        raise
    except Exception as e:
        print(f"Error: LLM A.2 Text Preprocessing API call failed: {e}")
        raise Exception(f"LLM A.2 Text Preprocessing API call failed: {e}") from e
