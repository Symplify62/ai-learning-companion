import requests
import hashlib
import hmac
import base64
import time
import os
import logging
import math
import json
import asyncio
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

from app.services.asr.base import AbstractAsrService

# Configure basic logging at the module level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SLICE_SIZE_MB = 10
BYTES_PER_MB = 1024 * 1024
DEFAULT_REQUEST_TIMEOUT = 60
PROGRESS_POLL_INTERVAL = 30
MAX_PROGRESS_POLLS = 120

# Define known status codes for clarity in _poll_progress
KNOWN_IN_PROGRESS_STATUSES = {0, 1, 2, 3, 4, 5}
KNOWN_FAILURE_STATUSES = {-1, 6, 7, 8}
SUCCESS_STATUS = 9

class XunfeiLfasrClient(AbstractAsrService):
    """
    A client for interacting with the iFlytek Long Form ASR (LFASR) API
    using the chunked/sliced audio file upload and transcription process.
    Based on documentation at: https://www.xfyun.cn/doc/asr/lfasr/API.html
    """

    class _SliceIdGenerator:
        """
        Generates sequential slice IDs (e.g., "aaaaaaaaaa", "aaaaaaaaab", ...).
        Each ID is 10 characters long, using 'a' through 'z'.
        """
        def __init__(self):
            self.current_id_list = ['a'] * 10
            self.char_set = "abcdefghijklmnopqrstuvwxyz"
            self.char_set_len = len(self.char_set)

        def _increment(self):
            for i in range(len(self.current_id_list) - 1, -1, -1):
                current_char_index = self.char_set.find(self.current_id_list[i])
                if current_char_index < self.char_set_len - 1:
                    self.current_id_list[i] = self.char_set[current_char_index + 1]
                    return
                else:
                    self.current_id_list[i] = self.char_set[0] # Wrap around
            # If we reach here, it means all characters wrapped around (e.g., "zzzzzzzzzz")
            # This case should ideally not be hit given the small number of slices expected.
            # For extreme cases, one might need a longer ID or a different scheme.
            logger.warning("Slice ID generator wrapped around. This is highly unlikely for typical files.")


        def get_next_id(self) -> str:
            """Returns the current ID and then increments for the next call."""
            current_id_str = "".join(self.current_id_list)
            self._increment()
            return current_id_str

    def __init__(self, appid: str, secret_key: str, host: str = "https://raasr.xfyun.cn/api/"):
        """
        Initializes the XunfeiLfasrClient.

        Args:
            appid (str): The application ID from iFlytek open platform.
            secret_key (str): The secret key associated with the application.
            host (str, optional): The API host URL. 
                                  Defaults to "https://raasr.xfyun.cn/api/".
        """
        self.appid = appid
        self.secret_key = secret_key
        self.host = host.rstrip('/') # Ensure no trailing slash
        self.session = requests.Session()
        logger.info(f"XunfeiLfasrClient initialized for appid: {appid[:5]}... host: {self.host}")

    def _generate_ts(self) -> str:
        """Generates the current timestamp string in seconds since epoch."""
        return str(int(time.time()))

    def _generate_signa(self, ts: str) -> str:
        """
        Generates the API signature (signa) required for authentication.

        Args:
            ts (str): The current timestamp string.

        Returns:
            str: The base64 encoded signature string.
        """
        base_string = self.appid + ts
        md5_hasher = hashlib.md5()
        md5_hasher.update(base_string.encode('utf-8'))
        md5_val = md5_hasher.hexdigest()

        hmac_sha1 = hmac.new(self.secret_key.encode('utf-8'), md5_val.encode('utf-8'), hashlib.sha1)
        signature_bytes = hmac_sha1.digest()
        
        signa = base64.b64encode(signature_bytes).decode('utf-8')
        return signa

    def _perform_synchronous_transcription(self, audio_file_path: str, language: str = "cn", 
                   has_participle: bool = False, speaker_number: int = 0, 
                   slice_size_mb: int = DEFAULT_SLICE_SIZE_MB, 
                   **other_prepare_params) -> Optional[List[Dict[str, Any]]]:
        """
        Synchronously transcribes the given audio file using the iFlytek LFASR service.
        This is the original implementation of the transcription logic.
        """
        logger.info(f"Starting transcription process for: {audio_file_path}")
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None

        try:
            file_len = os.path.getsize(audio_file_path)
            file_name = os.path.basename(audio_file_path)
            
            if file_len == 0:
                logger.error(f"Audio file is empty: {audio_file_path}")
                return None

            slice_data_size = slice_size_mb * BYTES_PER_MB
            slice_num = math.ceil(file_len / slice_data_size)
            if slice_num == 0 and file_len > 0:
                slice_num = 1
            
            logger.info(f"File: {file_name}, Size: {file_len} bytes, Slices: {slice_num} (slice_size_mb: {slice_size_mb})")

            task_id = self._call_prepare(
                file_len=file_len,
                file_name=file_name,
                slice_num=int(slice_num),
                language=language,
                has_participle=has_participle,
                speaker_number=speaker_number,
                **other_prepare_params
            )
            if not task_id:
                logger.error("Prepare call failed. Aborting transcription.")
                return None
            logger.info(f"Prepare call successful. Task ID: {task_id}")

            upload_success = self._upload_slices(
                audio_file_path=audio_file_path,
                task_id=task_id,
                file_len=file_len,
                slice_num=int(slice_num),
                slice_data_size=slice_data_size
            )
            if not upload_success:
                logger.error(f"Upload slices failed for task_id: {task_id}. Aborting transcription.")
                return None
            logger.info(f"All slices uploaded successfully for task_id: {task_id}.")

            merge_success = self._call_merge(task_id=task_id)
            if not merge_success:
                logger.error(f"Merge call failed for task_id: {task_id}. Aborting transcription.")
                return None
            logger.info(f"Merge call successful for task_id: {task_id}.")

            progress_complete = self._poll_progress(task_id=task_id)
            if not progress_complete:
                logger.error(f"Polling progress did not complete successfully or timed out for task_id: {task_id}. Aborting.")
                return None
            logger.info(f"Polling progress indicated task completion for task_id: {task_id}.")

            transcription_result = self._call_get_result(task_id=task_id)
            if not transcription_result:
                logger.error(f"Get result call failed for task_id: {task_id}.")
                return None
            
            logger.info(f"Transcription successful for task_id: {task_id}.")
            return transcription_result

        except Exception as e:
            logger.exception(f"An unexpected error occurred during the transcription process for {audio_file_path}: {e}")
            return None

    async def transcribe(self, audio_file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        Asynchronously transcribes the audio file using Xunfei Lfasr service.
        This method implements the AbstractAsrService interface.

        Args:
            audio_file_path: The path to the audio file to be transcribed.

        Returns:
            A list of segment dictionaries if transcription is successful,
            where each dictionary represents a recognized speech segment.
            Returns None if transcription fails or no segments are recognized.
        """
        try:
            # Run the synchronous transcription logic in a separate thread
            # to avoid blocking the asyncio event loop
            result = await asyncio.to_thread(
                self._perform_synchronous_transcription,
                audio_file_path
            )
            return result
        except Exception as e:
            logger.exception(f"Error during XunfeiLfasrClient.transcribe (async wrapper): {e}")
            return None

    # --- Implemented Private Methods --- #

    def _make_request(self, method: str, endpoint: str, 
                        params: dict = None, data_payload=None, files=None, 
                        is_form_data: bool = False, 
                        custom_headers: dict = None) -> requests.Response | None:
        """
        A generic helper method to make HTTP requests to the API.
        """
        full_url = self.host + endpoint
        headers = {}

        if method.upper() == "POST":
            if is_form_data:
                headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            # For `files` (multipart/form-data), requests sets Content-Type automatically.
            # No specific Content-Type logic needed here if `files` is used.
        
        if custom_headers:
            headers.update(custom_headers)

        log_params_str = str(params) if params else "{}"
        log_data_str = "Exists" if data_payload is not None else "None"
        log_files_str = "Exists" if files is not None else "None"
        logger.debug(f"Making request: {method} {full_url} | Headers: {headers} | Params: {log_params_str[:100]}... | Data: {log_data_str} | Files: {log_files_str}")
        
        try:
            # The `params` argument in requests.post is for URL query parameters.
            # The `data` argument is for the body (form data if Content-Type is x-www-form-urlencoded).
            # The `files` argument is for multipart/form-data.
            if method.upper() == "POST":
                # If `files` is present, `data_payload` usually isn't needed unless API mixes form fields with files in multipart
                # The LFASR /upload takes app_id, signa, ts, task_id, slice_id in URL params, and slice in `files`
                response = self.session.post(full_url, params=params, data=data_payload, files=files, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            elif method.upper() == "GET":
                response = self.session.get(full_url, params=params, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            logger.debug(f"Response received: {response.status_code} from {method} {full_url}")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {method} {full_url}: {e}")
            return None

    def _call_prepare(self, file_len: int, file_name: str, slice_num: int, 
                      language: str, has_participle: bool, speaker_number: int, 
                      **other_params) -> str | None:
        """
        Calls the /prepare API endpoint.
        Returns task_id on success, None otherwise.
        """
        endpoint = "/prepare"
        ts = self._generate_ts()
        signa = self._generate_signa(ts)

        payload = {
            "app_id": self.appid,
            "signa": signa,
            "ts": ts,
            "file_len": str(file_len),
            "file_name": file_name,
            "slice_num": slice_num, 
            "language": language,
            "has_participle": "true" if has_participle else "false",
            "speaker_number": str(speaker_number),
            "lfasr_type": "0" 
        }
        payload.update({str(k): str(v) for k, v in other_params.items()}) 
        
        logger.info(f"Calling /prepare with form data payload: {payload}")
        response = self._make_request(method="POST", endpoint=endpoint, data_payload=payload, is_form_data=True)

        if response is None:
            logger.error("/prepare request failed (network/request error).")
            return None

        if response.status_code == 200:
            try:
                response_json = response.json()
                logger.debug(f"/prepare response JSON: {response_json}")
                if response_json.get("ok") == 0 and response_json.get("err_no") == 0:
                    task_id = response_json.get("data")
                    if task_id:
                        logger.info(f"/prepare call successful. Task ID: {task_id}")
                        return task_id
                    else:
                        logger.error(f"/prepare successful but task_id (data) is missing in response: {response_json}")
                        return None
                else:
                    err_no = response_json.get("err_no")
                    failed_msg = response_json.get("failed")
                    logger.error(f"/prepare API error. err_no: {err_no}, message: {failed_msg}")
                    return None
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON response from /prepare: {response.text}")
                return None
            except KeyError as e:
                logger.error(f"Key missing in /prepare response JSON: {e}. Response: {response.text}")
                return None
        else:
            logger.error(f"/prepare request failed with status code {response.status_code}. Response: {response.text}")
            return None
    
    def _upload_slices(self, audio_file_path: str, task_id: str, 
                       file_len: int, slice_num: int, slice_data_size: int) -> bool:
        """
        Uploads audio file in slices to the /upload endpoint.
        Returns True on success, False otherwise.
        """
        endpoint = "/upload"
        slice_id_gen = self._SliceIdGenerator()
        bytes_uploaded = 0

        logger.info(f"Starting to upload {slice_num} slices for task_id: {task_id} from file: {audio_file_path}")

        try:
            with open(audio_file_path, 'rb') as audio_file:
                for i in range(slice_num):
                    slice_id = slice_id_gen.get_next_id()
                    
                    # Determine the actual size of data to read for this slice
                    # This is important for the last slice which might be smaller
                    current_slice_max_size = min(slice_data_size, file_len - bytes_uploaded)
                    slice_data = audio_file.read(current_slice_max_size)

                    if not slice_data:
                        if bytes_uploaded < file_len:
                            logger.error(f"Read empty slice prematurely for task_id: {task_id}, slice_id: {slice_id}. "
                                         f"Expected more data. Bytes uploaded: {bytes_uploaded}, File_len: {file_len}")
                            return False
                        else: # All data read, loop should have ended or slice_num was miscalculated
                            logger.warning(f"Read empty slice but all data seems uploaded for task_id: {task_id}. "
                                           f"Iteration {i+1}/{slice_num}. This might indicate slice_num mismatch if not the last slice.")
                            break # Exit loop if no more data

                    ts = self._generate_ts()
                    signa = self._generate_signa(ts)

                    query_params = {
                        "app_id": self.appid,
                        "signa": signa,
                        "ts": ts,
                        "task_id": task_id,
                        "slice_id": slice_id
                    }

                    files_payload = {'content': (slice_id, slice_data, 'application/octet-stream')}
                    
                    logger.info(f"Uploading slice {i+1}/{slice_num} (ID: {slice_id}, Size: {len(slice_data)} bytes) for task_id: {task_id}")

                    # _make_request's `params` argument handles URL query parameters
                    # `files` handles the multipart file upload
                    # `data_payload` should be None here for a pure file upload with query params.
                    response = self._make_request(method="POST", endpoint=endpoint, 
                                                  params=query_params, files=files_payload)

                    if response is None:
                        logger.error(f"Upload failed for task_id: {task_id}, slice_id: {slice_id} (network/request error).")
                        return False

                    if response.status_code == 200:
                        try:
                            response_json = response.json()
                            logger.debug(f"/upload response for slice {slice_id}: {response_json}")
                            if response_json.get("ok") == 0 and response_json.get("err_no") == 0:
                                logger.info(f"Successfully uploaded slice {slice_id} for task_id: {task_id}")
                                bytes_uploaded += len(slice_data)
                            else:
                                err_no = response_json.get("err_no")
                                failed_msg = response_json.get("failed")
                                logger.error(f"/upload API error for task_id: {task_id}, slice_id: {slice_id}. "
                                             f"err_no: {err_no}, message: {failed_msg}")
                                return False
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode JSON response from /upload for slice {slice_id}: {response.text}")
                            return False
                        except KeyError as e:
                            logger.error(f"Key missing in /upload response JSON for slice {slice_id}: {e}. Response: {response.text}")
                            return False
                    else:
                        logger.error(f"/upload request for slice {slice_id} failed with status code {response.status_code}. "
                                     f"Response: {response.text}")
                        return False
                
                # After loop completion, check if all bytes were uploaded
                if bytes_uploaded != file_len:
                    logger.error(f"Critical error: Mismatch after attempting to upload all slices for task_id: {task_id}. "
                                   f"Bytes uploaded: {bytes_uploaded}, Expected file_len: {file_len}. Upload failed.")
                    return False

        except FileNotFoundError:
            logger.error(f"Audio file not found during slice upload: {audio_file_path}")
            return False
        except IOError as e:
            logger.error(f"IOError during audio file processing for task_id {task_id}: {e}")
            return False
        except Exception as e:
            logger.exception(f"An unexpected error occurred during slice uploading for task_id {task_id}: {e}")
            return False
            
        logger.info(f"All {slice_num} slices appear to be uploaded successfully for task_id: {task_id}.")
        return True

    # --- Placeholder Private Methods --- #
    def _call_merge(self, task_id: str) -> bool:
        """
        Calls the /merge API endpoint to signal the server to merge slices and start transcription.

        Args:
            task_id (str): The task ID received from the /prepare call.

        Returns:
            bool: True if the merge call was successful, False otherwise.
        """
        endpoint = "/merge"
        ts = self._generate_ts()
        signa = self._generate_signa(ts)

        payload = {
            "app_id": self.appid,
            "signa": signa,
            "ts": ts,
            "task_id": task_id,
        }

        logger.info(f"Calling /merge for task_id: {task_id} with payload: {payload}")
        response = self._make_request(method="POST", endpoint=endpoint, data_payload=payload, is_form_data=True)

        if response is None:
            logger.error(f"/merge request failed for task_id: {task_id} (network/request error).")
            return False

        if response.status_code == 200:
            try:
                response_json = response.json()
                logger.debug(f"/merge response JSON for task_id {task_id}: {response_json}")
                if response_json.get("ok") == 0 and response_json.get("err_no") == 0:
                    logger.info(f"/merge call successful for task_id: {task_id}.")
                    return True
                else:
                    err_no = response_json.get("err_no")
                    failed_msg = response_json.get("failed")
                    logger.error(f"/merge API error for task_id: {task_id}. err_no: {err_no}, message: {failed_msg}")
                    return False
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON response from /merge for task_id {task_id}: {response.text}")
                return False
            except KeyError as e:
                logger.error(f"Key missing in /merge response JSON for task_id {task_id}: {e}. Response: {response.text}")
                return False
        else:
            logger.error(f"/merge request for task_id {task_id} failed with status code {response.status_code}. Response: {response.text}")
            return False

    def _poll_progress(self, task_id: str) -> bool:
        """
        Polls the /getProgress API endpoint until the task is complete or fails.
        Uses constants PROGRESS_POLL_INTERVAL and MAX_PROGRESS_POLLS.

        Args:
            task_id (str): The task ID to poll.

        Returns:
            bool: True if task completed successfully (status 9), False otherwise.
        """
        endpoint = "/getProgress"
        logger.info(f"Starting to poll progress for task_id: {task_id} every {PROGRESS_POLL_INTERVAL}s for max {MAX_PROGRESS_POLLS} attempts.")

        for attempt in range(MAX_PROGRESS_POLLS):
            if attempt > 0: # No sleep for the first attempt
                logger.debug(f"Polling attempt {attempt + 1}/{MAX_PROGRESS_POLLS} for task_id {task_id}. Sleeping for {PROGRESS_POLL_INTERVAL}s.")
                time.sleep(PROGRESS_POLL_INTERVAL)
            else:
                logger.debug(f"Polling attempt {attempt + 1}/{MAX_PROGRESS_POLLS} for task_id {task_id}.")

            ts = self._generate_ts()
            signa = self._generate_signa(ts)
            payload = {
                "app_id": self.appid,
                "signa": signa,
                "ts": ts,
                "task_id": task_id,
            }

            response = self._make_request(method="POST", endpoint=endpoint, data_payload=payload, is_form_data=True)

            if response is None:
                logger.error(f"/getProgress request failed for task_id: {task_id} (network/request error) on attempt {attempt + 1}.")
                # Depending on policy, we might retry a few times on network errors or fail fast.
                # For now, fail fast on network error during polling.
                return False 

            if response.status_code == 200:
                try:
                    response_json = response.json()
                    logger.debug(f"/getProgress response JSON for task_id {task_id} (attempt {attempt+1}): {response_json}")
                    
                    if not (response_json.get("ok") == 0 and response_json.get("err_no") == 0):
                        err_no = response_json.get("err_no")
                        failed_msg = response_json.get("failed")
                        logger.error(f"/getProgress API error for task_id: {task_id}. err_no: {err_no}, message: {failed_msg}. Aborting poll.")
                        return False

                    # The 'data' field is a JSON string itself
                    data_str = response_json.get("data")
                    if not data_str:
                        logger.error(f"/getProgress response for task_id {task_id} is missing 'data' field. Response: {response_json}")
                        # This is an unexpected API response format, likely an error state not caught by err_no
                        return False 
                    
                    inner_data_json = json.loads(data_str)
                    status = inner_data_json.get("status")
                    status_desc = inner_data_json.get("desc", "N/A") # Get description if available

                    logger.info(f"Progress for task_id {task_id}: Status {status} ('{status_desc}'). Attempt {attempt + 1}/{MAX_PROGRESS_POLLS}.")

                    # Status Interpretation (iFlytek LFASR Task Status Codes)
                    # 0:任务创建                (Task Created)
                    # 1:音频یوتیوب             (Audio Uploaded - this might be a typo in some docs, usually means processing started)
                    # 2:处理队列中             (In Processing Queue)
                    # 3:正在处理中             (Processing)
                    # 4:处理结果上传中          (Uploading Result)
                    # 5:处理完成              (Processing Complete - pre-merge or pre-final result)
                    # 9:转写结果上传完成       (Transcription Result Upload Complete - SUCCESS)
                    # -1:任务失败              (Task Failed)
                    # 6:上传音频异常/合并异常 (Upload/Merge Exception)
                    # 7:服务端内部配置异常    (Server Internal Configuration Error)
                    # 8:服务端内部异常        (Server Internal Error)

                    if status == SUCCESS_STATUS:
                        logger.info(f"Task {task_id} completed successfully (status {SUCCESS_STATUS}). Desc: '{status_desc}'.")
                        return True
                    elif status in KNOWN_FAILURE_STATUSES: # Failure codes
                        logger.error(f"Task {task_id} failed with status {status}. Desc: '{status_desc}'.")
                        return False
                    elif status in KNOWN_IN_PROGRESS_STATUSES: # In-progress codes
                        # Continue polling
                        pass 
                    else:
                        logger.error(f"Encountered unknown/unexpected status {status} for task_id {task_id}. Desc: '{status_desc}'. Aborting poll.")
                        return False # Treat unknown status as an error and stop polling

                except json.JSONDecodeError as e_json:
                    logger.error(f"Failed to decode JSON response from /getProgress for task_id {task_id} (attempt {attempt+1}): {response.text}. Error: {e_json}")
                    # Decide if we should retry or fail. For now, let's retry up to MAX_POLLS if it's a transient issue.
                except KeyError as e_key:
                    logger.error(f"Key missing in /getProgress response JSON for task_id {task_id} (attempt {attempt+1}): {e_key}. Response: {response.text}")
                    return False # Likely a permanent issue with response format
                except Exception as e_inner:
                    logger.exception(f"Unexpected error processing /getProgress response for task {task_id} (attempt {attempt+1}): {e_inner}")
                    return False

            else:
                logger.error(f"/getProgress request for task_id {task_id} failed with status code {response.status_code} (attempt {attempt+1}). Response: {response.text}")
                # Depending on policy, some HTTP errors might be retried. For now, fail fast on non-200 during polling.
                return False 

        logger.error(f"Polling for task_id {task_id} timed out after {MAX_PROGRESS_POLLS} attempts.")
        return False

    def _call_get_result(self, task_id: str) -> list | None:
        """
        Calls the /getResult API endpoint to fetch the transcription results after task completion.
        The 'data' field in the response is expected to be a JSON string representing a list of segments.

        Args:
            task_id (str): The task ID for which to fetch results.

        Returns:
            list | None: A list of transcription segment dictionaries if successful, None otherwise.
        """
        endpoint = "/getResult"
        ts = self._generate_ts()
        signa = self._generate_signa(ts)

        payload = {
            "app_id": self.appid,
            "signa": signa,
            "ts": ts,
            "task_id": task_id,
        }

        logger.info(f"Calling /getResult for task_id: {task_id} with payload: {payload}")
        response = self._make_request(method="POST", endpoint=endpoint, data_payload=payload, is_form_data=True)

        if response is None:
            logger.error(f"/getResult request failed for task_id: {task_id} (network/request error).")
            return None

        if response.status_code == 200:
            try:
                response_json = response.json()
                logger.debug(f"/getResult response JSON for task_id {task_id}: {response_json}")

                if not (response_json.get("ok") == 0 and response_json.get("err_no") == 0):
                    err_no = response_json.get("err_no")
                    failed_msg = response_json.get("failed")
                    logger.error(f"/getResult API error for task_id: {task_id}. err_no: {err_no}, message: {failed_msg}")
                    return None
                
                # The 'data' field is a JSON string representing an array of transcription segments.
                data_str = response_json.get("data")
                if data_str is None: # Check if data field is present and not None
                    logger.error(f"/getResult response for task_id {task_id} is missing 'data' field or it is null. Response: {response_json}")
                    return None
                
                transcription_list = json.loads(data_str)
                logger.info(f"Successfully fetched and parsed transcription results for task_id: {task_id}. Count: {len(transcription_list) if isinstance(transcription_list, list) else 'N/A'}")
                return transcription_list # Expected to be a list of dicts
            
            except json.JSONDecodeError as e_json_inner:
                logger.error(f"Failed to decode inner JSON 'data' string from /getResult for task_id {task_id}: {data_str}. Error: {e_json_inner}. Main Response: {response.text}")
                return None
            except TypeError as e_type: # Handles case where data_str might not be string-like for json.loads
                logger.error(f"Type error when attempting to parse 'data' field from /getResult for task_id {task_id}: {data_str}. Error: {e_type}. Main Response: {response.text}")
                return None
            except KeyError as e_key:
                logger.error(f"Key missing in /getResult response JSON for task_id {task_id}: {e_key}. Response: {response.text}")
                return None
            except Exception as e_getResult_inner:
                logger.exception(f"Unexpected error processing /getResult data for task {task_id}: {e_getResult_inner}")
                return None
        else:
            logger.error(f"/getResult request for task_id {task_id} failed with status code {response.status_code}. Response: {response.text}")
            return None

if __name__ == '__main__':
    logger.info("--- XunfeiLfasrClient E2E Test --- ")
    
    # Load environment variables from .env file
    load_dotenv()
    logger.info("Attempting to load credentials from .env file or environment variables.")

    # Attempt to get credentials from environment variables
    appid_from_env = os.environ.get("XUNFEI_APPID")
    secret_key_from_env = os.environ.get("XUNFEI_SECRET_KEY")

    if not appid_from_env:
        logger.critical("XUNFEI_APPID not found. Please define it in your .env file or as an environment variable (e.g., XUNFEI_APPID=your_actual_appid).")
    else:
        logger.info(f"XUNFEI_APPID loaded (partially masked): {appid_from_env[:5]}...")

    if not secret_key_from_env:
        logger.critical("XUNFEI_SECRET_KEY not found. Please define it in your .env file or as an environment variable (e.g., XUNFEI_SECRET_KEY=your_actual_secretkey).")
    else:
        logger.info(f"XUNFEI_SECRET_KEY loaded (partially masked): {secret_key_from_env[:5]}...")

    # Path to the WAV file produced by exAudio.py in the previous step.
    # This needs to be the exact path. The timestamp will change with each run of exAudio.py.
    # For a robust test, we should ideally discover this filename or pass it.
    # For now, let's assume we know the timestamp or can find the most recent one.
    
    # Discover the most recent WAV file in the target directory for robustness
    # This part of the test script assumes it's being run from a context where
    # "../temp_asr_input_audio" is a valid relative path to the audio files.
    # For example, if this script is in 'bili2text/' and audio in 'temp_asr_input_audio/' at workspace root.
    # When running from 'frontend_web', this relative path might be incorrect.
    # For direct execution of xunfei_lfasr_client.py, this logic is more for local testing.

    # Construct path relative to the script's directory for more robust local testing
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming temp_asr_input_audio is one level up from bili2text directory
    target_wav_directory_relative = os.path.join(script_dir, "..", "temp_asr_input_audio") 
    # For a more generic test, one might want to pass the audio file path as an argument or configure it
    
    # Let's use a placeholder for the audio file path for now, as the previous test code
    # had specific logic for finding "BV1ym9CYMExj_compliant_audio*.wav"
    # This test block is primarily for testing the client with credentials.
    # A more robust test would involve creating or providing a known audio file.
    
    # For this modification, we are focusing on credential loading.
    # The actual transcription part will only run if credentials AND a file are found.
    # To simplify, let's assume a test audio file named 'test_audio_sample.wav'
    # should be placed in the 'bili2text' directory alongside this script for this test block to run.
    
    placeholder_audio_file_name = "test_audio_sample.wav" # User should place this file for testing
    compliant_wav_file_path_for_transcription = os.path.join(script_dir, placeholder_audio_file_name)


    if not os.path.exists(compliant_wav_file_path_for_transcription):
        logger.warning(f"Test audio file '{placeholder_audio_file_name}' not found in script directory ({script_dir}).")
        logger.warning(f"Please place a '{placeholder_audio_file_name}' in that location for the test block to run transcription.")
        # We can still test credential loading part.
        compliant_wav_file_path_for_transcription = None # Set to None so transcription part is skipped.


    if appid_from_env and secret_key_from_env:
        if compliant_wav_file_path_for_transcription:
            logger.info(f"Credentials loaded. Proceeding with transcription for: {compliant_wav_file_path_for_transcription}")
            client = XunfeiLfasrClient(appid=appid_from_env, secret_key=secret_key_from_env)
            
            transcription_result = client.transcribe(
                audio_file_path=compliant_wav_file_path_for_transcription,
                language="cn", 
                has_participle=True, 
                speaker_number=0,    
                slice_size_mb=2      # Using 2MB slices for this test
            )

            if transcription_result:
                logger.info("--- Full Transcription Result ---")
                try:
                    pretty_result = json.dumps(transcription_result, indent=2, ensure_ascii=False)
                    logger.info(pretty_result)
                except Exception as e_json_dump:
                    logger.error(f"Could not serialize transcription result to JSON for pretty printing: {e_json_dump}")
                    logger.info(str(transcription_result)) # Fallback to string representation
                logger.info("--- End of Transcription Result ---")
            else:
                logger.error("Transcription failed or returned None.")
        else:
            logger.info("Credentials loaded, but no test audio file found. Skipping transcription test.")
            logger.info("To run the transcription test, ensure 'test_audio_sample.wav' is in the same directory as this script.")

    else:
        logger.critical("Cannot proceed with transcription client test due to missing credentials. Please check your .env file or environment variables.")

    logger.info("--- XunfeiLfasrClient E2E Test Finished --- ") 