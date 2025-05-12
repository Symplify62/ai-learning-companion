"""
LLM Caller for AI Module A.1 (Transcript Pre-processing & Metadata Generation)
"""
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional

from app.ai_modules.prompts_module_a1 import SYSTEM_PROMPT_A1_V1_1
from app.core.config import Settings # Used for type hinting settings parameter

async def invoke_module_a1_llm(
    parsed_transcript_segments: List[Dict[str, Any]], 
    user_input_title: Optional[str], 
    user_input_source_desc: Optional[str], 
    settings: Settings
) -> Dict[str, Any]:
    """
    Invokes the Google Gemini API for Module A.1 processing.

    @param parsed_transcript_segments: List of parsed transcript segments.
    @param user_input_title: Optional user-provided video title.
    @param user_input_source_desc: Optional user-provided source description.
    @param settings: Application settings instance containing the API key.
    @return: A dictionary containing the LLM's structured JSON output.
    @raise Exception: If API call fails or response format is invalid.
    """
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY.get_secret_value())
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Construct the user message
        # The system prompt expects keys: rawTranscriptSegments, userInputVideoTitle, userInputSourceDescription
        # We are directly providing parsed_transcript_segments as the value for rawTranscriptSegments
        # This matches the structure {"startTimeSeconds": float, "text": str} expected by the prompt for items in rawTranscriptSegments
        
        llm_input_structure = {
            "userInputVideoTitle": user_input_title,
            "userInputSourceDescription": user_input_source_desc,
            "rawTranscriptSegments": parsed_transcript_segments
        }

        user_message_content = f"""
Please process the following learning session data according to your instructions as the Stage 1 Transcript Pre-processor and Metadata Generator.

User Input:
Title: {user_input_title if user_input_title else 'Not provided'}
Source Description: {user_input_source_desc if user_input_source_desc else 'Not provided'}

Raw Transcript Segments to process:
```json
{json.dumps(parsed_transcript_segments, ensure_ascii=False, indent=2)}
```

Ensure your output is a single, valid JSON object adhering to the specified schema in your system prompt.
"""
        # For more direct mapping to the prompt's input description, 
        # we could also construct the user message purely as a JSON string for the LLM:
        # user_message_content_json_input = json.dumps(llm_input_structure, ensure_ascii=False, indent=2)
        # And then the prompt to LLM would be something like:
        # "Here is the input JSON: \n" + user_message_content_json_input + "\n Please process..."
        # However, the current mixed approach with clear text and an embedded JSON block is also common.
        # Sticking to the user's example structure for the user message content for now.

        print(f"Attempting to call Gemini for Module A.1. Input segments count: {len(parsed_transcript_segments)}")
        
        response = await model.generate_content_async(
            [SYSTEM_PROMPT_A1_V1_1, user_message_content],
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                # Consider adding response_mime_type="application/json" if supported and desired for Gemini
                # For now, we expect the LLM to produce a JSON string within its text response due to prompt instructions
            )
        )

        if not response.candidates or not response.candidates[0].content.parts:
            print("Error: Gemini API returned no content or invalid content structure.")
            raise ValueError("Gemini API returned no content.")

        llm_response_text = response.candidates[0].content.parts[0].text
        
        # The LLM is instructed to return a single valid JSON object.
        # Sometimes, the LLM might wrap the JSON in ```json ... ```. We need to strip that.
        if llm_response_text.strip().startswith("```json"):
            llm_response_text = llm_response_text.strip()[7:] # Remove ```json

            if llm_response_text.strip().endswith("```"):
                llm_response_text = llm_response_text.strip()[:-3] # Remove ```
        
        llm_response_text = llm_response_text.strip()

        try:
            parsed_output = json.loads(llm_response_text)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse LLM JSON response for Module A.1. Error: {e}")
            print(f"LLM Raw Response Text was:\n{llm_response_text}")
            raise ValueError(f"LLM response was not valid JSON: {e}")

        # Basic Validation (MVP)
        required_keys = ["videoId", "videoTitle", "transcriptSegments"]
        for key in required_keys:
            if key not in parsed_output:
                print(f"Error: LLM response for Module A.1 missing required key: {key}")
                print(f"LLM Parsed Output was:\n{parsed_output}")
                raise ValueError(f"LLM response for A.1 missing key: {key}")
        
        if not isinstance(parsed_output["transcriptSegments"], list):
            print(f"Error: LLM response for Module A.1 'transcriptSegments' is not a list.")
            print(f"LLM Parsed Output was:\n{parsed_output}")
            raise ValueError("'transcriptSegments' in LLM A.1 response must be a list.")

        print("Successfully received and parsed response from Gemini for Module A.1.")
        return parsed_output

    except genai.types.BlockedPromptException as e:
        print(f"Error: Gemini API call for Module A.1 was blocked. Details: {e}")
        # Potentially inspect e.block_reason or similar attributes if available
        raise Exception(f"Gemini API call blocked (A.1): Safety reasons or other. {e}")
    except Exception as e:
        print(f"Error during Module A.1 LLM call: {str(e)}")
        # Log the full exception details if possible
        # import traceback
        # print(traceback.format_exc())
        raise Exception(f"Module A.1 LLM call failed: {str(e)}") 