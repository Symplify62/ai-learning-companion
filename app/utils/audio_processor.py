import subprocess
import os
import time
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_audio_with_ffmpeg(video_path: str, output_wav_path: str) -> bool:
    """
    Extracts audio from a video file using ffmpeg and converts it to a
    single WAV file with specified ASR-friendly parameters (16kHz, mono, 16-bit PCM).

    Args:
        video_path (str): The full path to the input video file.
        output_wav_path (str): The desired full path for the output WAV file.

    Returns:
        bool: True if extraction was successful, False otherwise.
    """
    if not os.path.exists(video_path):
        logging.error(f"Input video file not found: {video_path}")
        return False

    # ffmpeg command construction
    # -i: input file
    # -y: overwrite output files without asking
    # -hide_banner: suppress printing banner
    # -loglevel error: show only errors
    # -vn: disable video recording (extract audio only)
    # -acodec pcm_s16le: audio codec, PCM signed 16-bit little-endian (standard for WAV)
    # -ar 16000: audio sample rate 16kHz
    # -ac 1: audio channels, 1 for mono
    command = [
        'ffmpeg',
        '-i', video_path,
        '-y',
        '-hide_banner',
        '-loglevel', 'error',
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        output_wav_path
    ]

    logging.info(f"Executing ffmpeg command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logging.info(f"ffmpeg successfully extracted audio to: {output_wav_path}")
            return True
        else:
            logging.error(f"ffmpeg command failed with return code {result.returncode}")
            logging.error(f"ffmpeg stderr: {result.stderr.strip()}")
            return False
    except FileNotFoundError:
        logging.error("ffmpeg command not found. Please ensure ffmpeg is installed and in your system PATH.")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred while running ffmpeg: {e}")
        logging.error(f"ffmpeg stderr: {result.stderr.strip() if 'result' in locals() else 'N/A'}")
        return False

def prepare_audio_for_asr(video_name_no_ext: str, 
                          video_input_folder: str = 'bilibili_video', 
                          audio_output_folder: str = "audio/full_audio",
                          output_filename_no_ext: str = "") -> str | None:
    """
    Processes a video file to extract a single, ASR-compliant WAV audio file using ffmpeg.

    Args:
        video_name_no_ext (str): The base name of the video file (without extension).
                                 It's assumed the video is an MP4 file or other ffmpeg-compatible format.
        video_input_folder (str): The directory where the input video file is located.
        audio_output_folder (str): The directory where the final WAV audio file will be saved.
        output_filename_no_ext (str): The base name of the output file (without extension).

    Returns:
        str | None: The path to the generated compliant WAV audio file, or None if an error occurs.
    """
    input_video_path = os.path.join(video_input_folder, f"{video_name_no_ext}.mp4") # Assuming .mp4, adjust if needed

    if not os.path.exists(input_video_path):
        logging.error(f"Video file not found for processing: {input_video_path}")
        return None

    try:
        os.makedirs(audio_output_folder, exist_ok=True)
        logging.info(f"Ensured output directory exists: {audio_output_folder}")
    except OSError as e:
        logging.error(f"Could not create output directory {audio_output_folder}: {e}")
        return None

    timestamp = time.strftime('%Y%m%d%H%M%S')
    output_filename = f"{output_filename_no_ext}_{timestamp}.wav" if output_filename_no_ext else f"{video_name_no_ext}_{timestamp}.wav"
    output_wav_path = os.path.join(audio_output_folder, output_filename)

    logging.info(f"Preparing audio for ASR from video: {input_video_path}")
    logging.info(f"Target output WAV path: {output_wav_path}")

    success = extract_audio_with_ffmpeg(input_video_path, output_wav_path)

    if success:
        logging.info(f"ASR-compliant audio successfully prepared at: {output_wav_path}")
        return output_wav_path
    else:
        logging.error(f"Failed to prepare ASR-compliant audio for: {video_name_no_ext} from {input_video_path}")
        # Attempt to clean up potentially empty/corrupt output file if ffmpeg failed
        if os.path.exists(output_wav_path):
            try:
                if os.path.getsize(output_wav_path) == 0: # Check if file is empty
                    os.remove(output_wav_path)
                    logging.info(f"Removed empty/corrupt output file: {output_wav_path}")
            except OSError as e_remove:
                logging.warning(f"Could not remove potentially corrupt output file {output_wav_path}: {e_remove}")
        return None

if __name__ == '__main__':
    logging.info("--- Running exAudio.py Test (ffmpeg version) ---")
    logging.info("IMPORTANT: This test requires ffmpeg to be installed and accessible in your system PATH.")

    # --- Configuration for the test ---
    # Option 1: Use a placeholder. The script will try to create a dummy video if it doesn't exist.
    # This dummy video creation is basic and might fail if ffmpeg has issues with the command.
    test_video_name = "sample_ffmpeg_test_video"
    test_input_dir = "bili2text_test_videos_ffmpeg" # Keep test files separate
    test_output_dir = "audio/test_output_ffmpeg"

    # Option 2: Manually place a video file (e.g., an MP4) in test_input_dir
    # and update test_video_name accordingly.
    # e.g., test_video_name = "my_actual_test_video" (without .mp4)
    # For the Bilibili video previously downloaded (if available):
    # test_video_name = "BV1ym9CYMExj_downloaded"
    # test_input_dir = "bili2text_test_videos" # or wherever it was saved
    # ------------------------------------

    # Ensure test input directory exists for dummy video creation
    if not os.path.exists(test_input_dir):
        os.makedirs(test_input_dir, exist_ok=True)
        logging.info(f"Created test input directory: {test_input_dir}")

    dummy_video_full_path = os.path.join(test_input_dir, f"{test_video_name}.mp4")

    # Create a dummy MP4 video file for testing if it doesn't exist
    # This is a very basic dummy video and might not be suitable for all ffmpeg installations.
    # A real video file is always better for testing.
    if not os.path.exists(dummy_video_full_path):
        logging.info(f"Test video not found at {dummy_video_full_path}. Attempting to create a dummy video.")
        # Command to create a 1-second black video with silent audio
        dummy_create_command = [
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=1280x720:r=1',
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-t', '1', '-pix_fmt', 'yuv420p', dummy_video_full_path,
            '-hide_banner', '-loglevel', 'error'
        ]
        try:
            logging.info(f"Executing dummy video creation: {' '.join(dummy_create_command)}")
            dummy_result = subprocess.run(dummy_create_command, capture_output=True, text=True, check=False)
            if dummy_result.returncode == 0:
                logging.info(f"Successfully created dummy video: {dummy_video_full_path}")
            else:
                logging.error(f"Failed to create dummy video. ffmpeg stderr: {dummy_result.stderr.strip()}")
                logging.error("Please place a valid MP4 video in the 'bili2text_test_videos_ffmpeg' directory and update 'test_video_name' for testing.")
                test_video_name = None # Prevent further processing if dummy creation failed
        except FileNotFoundError:
            logging.error("ffmpeg not found. Cannot create dummy video or run tests.")
            test_video_name = None # Prevent further processing
        except Exception as e_dummy:
            logging.error(f"Error creating dummy video: {e_dummy}")
            test_video_name = None # Prevent further processing
    else:
        logging.info(f"Using existing test video: {dummy_video_full_path}")

    if test_video_name:
        logging.info(f"Attempting to process video: {test_video_name}")
        output_wav = prepare_audio_for_asr(
            video_name_no_ext=test_video_name,
            video_input_folder=test_input_dir,
            audio_output_folder=test_output_dir
        )

        if output_wav:
            logging.info(f"Test successful! Compliant audio generated at: {os.path.abspath(output_wav)}")
            logging.info("Please verify the audio properties (16kHz, mono, 16-bit WAV pcm_s16le).")
            # Example of how to verify with ffprobe (if user wants to run manually):
            # logging.info(f"To verify, you can use: ffprobe -v error -show_streams -select_streams a:0 \"{os.path.abspath(output_wav)}\"")
        else:
            logging.error(f"Test failed for video: {test_video_name}")
    else:
        logging.warning("Test skipped as no valid test video was available or could be created.")

    # Test with a dummy MP4 file (replace with a real MP4 for actual testing)
    # dummy_video_name = "test_video_dummy"
    # dummy_input_folder = "bilibili_video" # Create this folder and put a test.mp4
    # dummy_output_folder = "audio/full_audio_test_dummy"
    # dummy_video_path = os.path.join(dummy_input_folder, dummy_video_name + '.mp4')

    # if not os.path.exists(dummy_input_folder):
    #     os.makedirs(dummy_input_folder)
    # # Create a small, short dummy MP4 if it doesn't exist (requires ffmpeg)
    # # This is just for basic script execution test, not for ASR quality test.
    # if not os.path.exists(dummy_video_path):
    #     logging.info(f"Attempting to create dummy video: {dummy_video_path}")
    #     try:
    #         subprocess.run([
    #             'ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc=duration=1:size=qcif:rate=10',
    #             '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=1',
    #             '-shortest', dummy_video_path,
    #             '-hide_banner', '-loglevel', 'error'
    #         ], check=True, timeout=10)
    #         logging.info(f"Dummy video created: {dummy_video_path}")
    #     except FileNotFoundError:
    #         logging.error("ffmpeg not found. Cannot create dummy video for test. Please create it manually or provide a real one.")
    #         dummy_video_path = None
    #     except subprocess.TimeoutExpired:
    #         logging.error(f"ffmpeg command timed out during dummy video creation for {dummy_video_path}")
    #         dummy_video_path = None
    #     except subprocess.CalledProcessError as e_ffmpeg:
    #         logging.error(f"ffmpeg failed to create dummy video: {e_ffmpeg}. Stderr: {e_ffmpeg.stderr}")
    #         dummy_video_path = None
    #     except Exception as e_dummy_create:
    #         logging.error(f"Failed to create dummy video {dummy_video_path}: {e_dummy_create}")
    #         dummy_video_path = None 
    
    # if dummy_video_path and os.path.exists(dummy_video_path):
    #     logging.info(f"--- Running exAudio.py Test with Dummy Video ---")
    #     output_wav = prepare_audio_for_asr(dummy_video_name, video_input_folder=dummy_input_folder, audio_output_folder=dummy_output_folder)
    #     if output_wav:
    #         logging.info(f"Dummy audio extraction successful: {output_wav}")
    #     else:
    #         logging.error("Dummy audio extraction failed.")
    # else:
    #     logging.info(f"Test with dummy video skipped: Dummy video {dummy_video_path} could not be created/found. Please place a real MP4 video for testing.")

    # --- Test for Bilibili Video --- #
    logging.info("--- Running exAudio.py Test with Bilibili Video ---")
    bili_video_name = "BV1ym9CYMExj" # Without .mp4 extension
    bili_input_folder = "temp_bili_download" # Relative to workspace root
    bili_output_folder = "temp_asr_input_audio" # Relative to workspace root
    # Let's make the output filename more specific
    specific_output_filename = f"{bili_video_name}_compliant_audio.wav"

    logging.info(f"Attempting to process: {bili_video_name}.mp4 from {bili_input_folder}")
    logging.info(f"Output will be saved to: {bili_output_folder}/{specific_output_filename}")

    # Ensure paths are constructed from workspace root if script is run from elsewhere
    # However, exAudio.py constructs paths relative to its own location or CWD if not careful.
    # The prepare_audio_for_asr function uses os.path.join, so relative paths should work if
    # the script is executed from workspace root or one level down like frontend_web.

    output_wav_path = prepare_audio_for_asr(
        video_name_no_ext=bili_video_name,
        video_input_folder=os.path.join("..", bili_input_folder), # Adjust path relative to bili2text directory
        audio_output_folder=os.path.join("..", bili_output_folder),
        output_filename_no_ext=bili_video_name + "_compliant_audio" # Pass filename without .wav
    )

    if output_wav_path:
        logging.info(f"Bilibili video audio extraction successful. Compliant WAV saved to: {output_wav_path}")
        # Verify if the output file actually exists at the reported path
        # The output_wav_path is relative to where exAudio.py is, so to check from workspace root:
        expected_full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), output_wav_path))
        logging.info(f"Absolute path to check: {expected_full_path}")
        if os.path.exists(expected_full_path):
            logging.info(f"Confirmed: WAV file exists at {expected_full_path}")
        else:
            logging.error(f"Verification FAILED: WAV file NOT found at {expected_full_path}")
            logging.error(f"Note: prepare_audio_for_asr returned {output_wav_path} which resolves to the above.")

    else:
        logging.error("Bilibili video audio extraction failed.")
    logging.info("--- exAudio.py Test Finished ---") 