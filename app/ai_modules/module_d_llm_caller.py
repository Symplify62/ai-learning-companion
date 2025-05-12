"""
LLM Caller for AI Module D (Knowledge Point Cue Generation)
"""
import json
import re
import uuid # For cueId generation
from typing import Dict, Any, List, Optional

import google.generativeai as genai

from app.core.config import Settings
from app.ai_modules.prompts_module_d import SYSTEM_PROMPT_D_V1_0

async def invoke_module_d_llm(
    note_markdown_content: str, 
    key_concepts_list: Optional[List[str]], 
    note_summary: Optional[str], 
    video_id: str, 
    note_id: str, 
    settings: Settings
) -> Dict[str, Any]:
    """
    Invokes the Gemini LLM for Module D to generate knowledge point cues.

    Args:
        note_markdown_content: The Markdown content of the study note.
        key_concepts_list: Optional list of key concepts from the note.
        note_summary: Optional summary of the note.
        video_id: The ID of the video.
        note_id: The ID of the note.
        settings: The application settings instance.

    Returns:
        A dictionary containing the LLM's structured output for Module D.

    Raises:
        ValueError: If the LLM response is invalid or missing required fields.
        Exception: For other LLM API call failures.
    """
    print(f"Attempting to call Gemini for Module D. Processing noteId: {note_id} for videoId: {video_id}")

    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY.get_secret_value())
        model = genai.GenerativeModel('gemini-1.5-flash')

        user_message_content = f"""Please generate knowledge reinforcement cues based on the following study note content and its context, according to your detailed instructions (SYSTEM_PROMPT_D_V1_0).

Video ID: {video_id}
Note ID: {note_id}

Note Summary:
{note_summary if note_summary else "Not available."}

Key Concepts Mentioned in the Note:
{json.dumps(key_concepts_list, ensure_ascii=False, indent=2) if key_concepts_list else "Not available."}

Full Note Markdown Content to process:
```markdown
{note_markdown_content}
```

Ensure your output is a single, valid JSON object as specified in your system prompt for Module D.
This includes:
- Passing through videoId: "{video_id}"
- Passing through noteId: "{note_id}"
- Generating a placeholder for `generationTimestamp` like "[SYSTEM_GENERATED_TIMESTAMP_YYYY-MM-DDTHH:MM:SSZ]".
- Generating a `knowledgeCues` list containing exactly five (5) items, with two (2) "low" difficulty and three (3) "high" difficulty, unless the note content is too short.
- Each cue item must have a unique `cueId` (e.g., UUID-like string), `questionText`, `answerText`, `difficultyLevel` ("low" or "high"), and `sourceReferenceInNote`.
All textual content in the cues must be in the same language as the input note.
"""
        
        print(f"Module D LLM User Message prepared. Length: {len(user_message_content)} chars.")
        # print(f"Module D LLM User Message snippet: {user_message_content[:500]}...") # Uncomment for debugging

        response = await model.generate_content_async(
            [SYSTEM_PROMPT_D_V1_0, user_message_content],
            generation_config=genai.types.GenerationConfig(temperature=0.75)
        )

        print("LLM D call successful. Response received.")
        
        response_text = response.text
        # Strip markdown ```json ... ``` wrapper if present
        match = re.search(r"```json\n(.*)\n```", response_text, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned_response_text = match.group(1).strip()
        else:
            cleaned_response_text = response_text.strip()
            if not (cleaned_response_text.startswith('{') and cleaned_response_text.endswith('}')):
                 print("Warning: LLM D might have outputted text that is not a JSON object. Raw response will be used for parsing attempt.")


        parsed_output = json.loads(cleaned_response_text)
        print("LLM D response parsed successfully.")

        # Basic Validation
        if not isinstance(parsed_output, dict):
            raise ValueError("LLM D response is not a JSON object.")
        
        # Validate videoId and noteId
        if parsed_output.get("videoId") != video_id:
            print(f"Warning: LLM D videoId '{parsed_output.get('videoId')}' differs from input '{video_id}'. Overwriting.")
            parsed_output["videoId"] = video_id
        
        if parsed_output.get("noteId") != note_id:
            print(f"Warning: LLM D noteId '{parsed_output.get('noteId')}' differs from input '{note_id}'. Overwriting.")
            parsed_output["noteId"] = note_id

        # Validate knowledgeCues structure
        if "knowledgeCues" not in parsed_output:
            raise ValueError("LLM D response missing required field: 'knowledgeCues'.")
        if not isinstance(parsed_output["knowledgeCues"], list):
            raise ValueError("LLM D response field 'knowledgeCues' is not a list.")

        knowledge_cues = parsed_output["knowledgeCues"]
        # With dynamic prompt V1.2, the number of cues can vary.
        # The old warning for != 5 cues is less critical but can remain for now.
        if len(knowledge_cues) != 5: # This check was based on the old prompt.
            print(f"Info: LLM D generated {len(knowledge_cues)} cues. (Prompt is now dynamic, so count can vary).")

        # Validate each cue
        required_cue_fields = {
            "cueId": str,
            "questionText": str,
            "answerText": str,
            "difficultyLevel": str,
            "sourceReferenceInNote": str
        }
        # Updated difficulty tracking
        difficulty_counts = {"low": 0, "medium": 0, "high": 0, "unknown": 0}

        for i, cue in enumerate(knowledge_cues):
            if not isinstance(cue, dict):
                raise ValueError(f"LLM D: Item at index {i} in 'knowledgeCues' is not a dictionary.")
            for field, field_type in required_cue_fields.items():
                if field not in cue:
                    raise ValueError(f"LLM D: Cue at index {i} missing required field: '{field}'. Cue: {cue}")
                if not isinstance(cue[field], field_type):
                    raise ValueError(f"LLM D: Cue at index {i} field '{field}' has incorrect type. Expected {field_type}, got {type(cue[field])}. Cue: {cue}")
            
            difficulty = cue.get("difficultyLevel")
            # Updated validation for difficultyLevel
            valid_difficulties = ["low", "medium", "high"]
            if difficulty not in valid_difficulties:
                # Allow "unknown" if LLM fails to provide a valid one, but log it.
                # Or raise error: raise ValueError(f"LLM D: Cue at index {i} has invalid 'difficultyLevel': '{difficulty}'. Must be one of {valid_difficulties}.")
                print(f"Warning: LLM D: Cue at index {i} has invalid 'difficultyLevel': '{difficulty}'. Expected one of {valid_difficulties}. Marking as unknown.")
                difficulty_counts["unknown"] += 1
                cue["difficultyLevel"] = "medium" # Default to medium if invalid, or handle as error
            else:
                difficulty_counts[difficulty] += 1
        
        # Log difficulty mix
        print(f"Info: LLM D: Generated {len(knowledge_cues)} cues with the following difficulty distribution: "
              f"{difficulty_counts['low']} low, {difficulty_counts['medium']} medium, {difficulty_counts['high']} high, {difficulty_counts['unknown']} unknown.")

        # generationTimestamp is handled by orchestrator if placeholder

        print(f"LLM D output validated. Generated {len(knowledge_cues)} cues.")
        return parsed_output

    except json.JSONDecodeError as e:
        print(f"Error: LLM D JSON parsing error: {e}")
        print(f"LLM D Raw problematic response text: '{response_text if 'response_text' in locals() else 'Response text not available'}'")
        raise ValueError(f"LLM D failed to produce valid JSON: {e}") from e
    except ValueError as ve: # Catch validation errors
        print(f"Error: LLM D Validation Error: {ve}")
        # print(f"LLM D problematic parsed output: {json.dumps(parsed_output, indent=2) if 'parsed_output' in locals() else 'Parsed output not available'}")
        raise
    except Exception as e:
        print(f"Error: LLM D API call failed: {e}")
        raise Exception(f"LLM D API call failed: {e}") from e 