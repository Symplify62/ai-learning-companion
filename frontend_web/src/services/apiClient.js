/**
 * @file apiClient.js
 * @description Centralized API client module for making requests to the backend.
 */

// Import the environment variable for the base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
// Define the API prefix centrally
const API_PREFIX = '/api/v1';

/**
 * Base request function for making API calls.
 * Handles URL construction, request options, and basic response/error handling.
 *
 * @async
 * @function request
 * @param {string} endpoint - The API endpoint (e.g., '/learning_sessions/'). Must start with '/'.
 * @param {object} [options={}] - Optional configuration for the fetch call.
 * @param {string} [options.method='GET'] - HTTP method (GET, POST, PUT, DELETE, etc.).
 * @param {object|string} [options.body=null] - The request body for methods like POST or PUT.
 * @param {object} [options.headers={}] - Custom headers to merge with default headers.
 * @returns {Promise<any>} - A promise that resolves with the parsed JSON response or null for 204 No Content.
 * @throws {Error} - Throws an error for network issues or non-successful HTTP statuses.
 *                   The error object will have `status`, `statusText`, and `data` (parsed error response) properties if it's an HTTP error.
 */
async function request(endpoint, options = {}) {
  // Validate endpoint format
  if (!endpoint || !endpoint.startsWith('/')) {
    const errorMsg = `API Client Error: Endpoint must start with '/'. Received: ${endpoint}`;
    console.error(errorMsg);
    throw new Error(errorMsg);
  }

  // Construct the full URL
  // Ensure API_BASE_URL doesn't have a trailing slash and API_PREFIX starts with one.
  const cleanBaseUrl = API_BASE_URL ? (API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL) : '';
  if (!cleanBaseUrl) {
      console.error("API Client Error: VITE_API_BASE_URL is not defined or empty.");
      throw new Error("API base URL is not configured.");
  }
  const fullUrl = `${cleanBaseUrl}${API_PREFIX}${endpoint}`;

  const { method = 'GET', body = null, headers: customHeaders = {} } = options;

  const fetchOptions = {
    method: method,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...customHeaders, // Merge custom headers, allowing override of defaults
    },
  };

  // Add body if present and method is appropriate
  // For 'GET' or 'HEAD' requests, body should not be included.
  const methodsWithBody = ['POST', 'PUT', 'PATCH', 'DELETE']; // DELETE can sometimes have a body, though not standard.
  if (body && methodsWithBody.includes(method.toUpperCase())) {
    fetchOptions.body = JSON.stringify(body);
  } else if (body && !methodsWithBody.includes(method.toUpperCase())) {
    console.warn(`API Client Warning: Body provided for HTTP method ${method} which typically does not support it. Body will be ignored.`);
  }


  // console.debug(`API Request: ${method} ${fullUrl}`, fetchOptions);

  try {
    const response = await fetch(fullUrl, fetchOptions);
    // console.debug(`API Response Status: ${response.status} ${response.statusText} for ${fullUrl}`);

    // Handle No Content response
    if (response.status === 204) {
      return null; 
    }

    let responseData = null;
    const contentType = response.headers.get("content-type");

    if (contentType && contentType.includes("application/json")) {
      try {
        responseData = await response.json();
      } catch (jsonError) {
        // If response.ok is true but JSON parsing fails, it's a server/data issue.
        if (response.ok) {
          console.error(`API Client Error: Failed to parse valid JSON response from ${fullUrl} (Status: ${response.status}). Content-Type was 'application/json'.`, jsonError);
          throw new Error(`Failed to parse JSON response from server, although status was ${response.status}.`);
        }
        // If response.ok is false, parsing error body might fail.
        // The error will be constructed below using response.statusText if responseData remains null.
        console.warn(`API Client Warning: Failed to parse error JSON from ${fullUrl} (Status: ${response.status}). Content-Type was 'application/json'.`, jsonError);
        // Store a generic detail if parsing the error JSON failed, so the error thrown below has some context
        responseData = { detail: `Server returned ${response.status}, but error body was not valid JSON or empty.` };
      }
    } else if (response.ok && contentType && !contentType.includes("application/json")) {
      // Handle successful responses that are not JSON (e.g., text/plain)
      // console.warn(`API Client Warning: Received non-JSON success response (Content-Type: ${contentType}) from ${fullUrl}. Returning as text.`);
      // return await response.text(); // Or handle based on expected content types
      // For now, if not JSON and successful, and not 204, treat as unexpected unless explicitly handled.
      // If it's truly successful but not JSON, the caller needs to know or it should be handled.
      // For this generic client, we'll assume JSON is expected for successful data returns other than 204.
       console.warn(`API Client Warning: Successful response from ${fullUrl} was not JSON (Content-Type: ${contentType}). Returning null as per current design.`);
       return null; // Or throw an error if JSON was strictly expected for all non-204 success
    }


    if (!response.ok) {
      // Use a more descriptive message if available from parsed JSON error, otherwise default.
      const message = (responseData && responseData.detail) 
                      ? (Array.isArray(responseData.detail) ? responseData.detail.map(d => d.msg || JSON.stringify(d)).join('; ') : responseData.detail) 
                      : `HTTP error! Status: ${response.status} ${response.statusText}`;
      
      const error = new Error(message);
      error.status = response.status;
      error.statusText = response.statusText;
      error.response = response; 
      error.data = responseData; 
      // console.error(`API Client HTTP Error: ${error.status} ${error.message}`, error.data || '');
      throw error;
    }

    return responseData; // Parsed JSON data for successful responses

  } catch (networkOrThrownError) {
    // Log and re-throw the error. If it's our custom HTTP error, it already has details.
    // If it's a network error from fetch itself, it won't have .status property.
    if (networkOrThrownError.status) { // It's one of our custom errors thrown above
        console.error(`API Client Re-thrown Error: ${networkOrThrownError.status} ${networkOrThrownError.message}`, networkOrThrownError.data || '');
        throw networkOrThrownError;
    } else { // It's a network error or other exception during fetch/setup
        console.error(`API Client Network/Fetch Error for ${method} ${fullUrl}:`, networkOrThrownError.message);
        throw new Error(`Network error or problem executing fetch: ${networkOrThrownError.message}`);
    }
  }
}

// Module will later export specific functions that use this 'request' function.
// e.g.:
// export async function getLearningSessionStatus(sessionId) {
//   return request(`/learning_sessions/${sessionId}/status`, { method: 'GET' });
// }
//
// export async function createLearningSession(data) {
//   return request('/learning_sessions/', { method: 'POST', body: data });
// }

/**
 * Creates a new learning session via the backend API.
 * @param {object} data - The request body.
 * @param {'url'|'text'} data.source_type - The type of the learning source. (Example, actual expected fields may vary based on backend)
 * @param {string} data.source_content - The URL or text content. (Example)
 * @returns {Promise<object>} A promise that resolves with the API response (e.g., { sessionId: string, status: string }).
 * @throws {Error} Throws an error if the API request fails (forwarded from the base request function).
 */
export async function createLearningSession(data) {
  return request('/learning_sessions/', {
    method: 'POST',
    body: data,
  });
}

/**
 * Fetches the current status of a specific learning session.
 * @param {string} sessionId - The ID of the learning session to query.
 * @returns {Promise<object>} A promise that resolves with the status API response
 * (e.g., { status: string, progress?: number, details?: string, final_result_available?: boolean }).
 * The exact shape depends on the backend endpoint.
 * @throws {Error} Throws an error if the API request fails (forwarded from the base request function).
 */
export async function getLearningSessionStatus(sessionId) {
  if (!sessionId) {
    console.error("API Client Error: sessionId is required for getLearningSessionStatus.");
    throw new Error("sessionId is required to fetch session status.");
  }
  return request(`/learning_sessions/${sessionId}/status`, {
    method: 'GET',
  });
}

/**
 * Fetches the generated notes for a specific learning session.
 * @param {string} sessionId - The ID of the learning session.
 * @returns {Promise<Array<object>>} A promise that resolves with an array of note objects
 * (e.g., [{ note_id: string, markdown_content: string, summary_of_note?: string, ... }]).
 * The exact shape depends on the backend endpoint.
 * @throws {Error} Throws an error if the API request fails (forwarded from the base request function).
 */
export async function getLearningSessionNotes(sessionId) {
  if (!sessionId) {
    console.error("API Client Error: sessionId is required for getLearningSessionNotes.");
    throw new Error("sessionId is required to fetch session notes.");
  }
  return request(`/learning_sessions/${sessionId}/notes`, {
    method: 'GET',
  });
}

/**
 * Fetches the generated knowledge cues for a specific note.
 * @param {string} noteId - The ID of the note for which to fetch knowledge cues.
 * @returns {Promise<Array<object>>} A promise that resolves with an array of knowledge cue objects
 * (e.g., [{ cue_id: string, question_text: string, answer_text: string, difficulty_level?: string, ... }]).
 * The exact shape depends on the backend endpoint.
 * @throws {Error} Throws an error if the API request fails (forwarded from the base request function).
 */
export async function getLearningSessionKnowledgeCues(noteId) {
  if (!noteId) {
    console.error("API Client Error: noteId is required for getLearningSessionKnowledgeCues.");
    throw new Error("noteId is required to fetch knowledge cues.");
  }
  return request(`/learning_sessions/notes/${noteId}/knowledge_cues`, {
    method: 'GET',
  });
}

export {}; // Add an empty export to ensure it's treated as a module if no other exports yet. 