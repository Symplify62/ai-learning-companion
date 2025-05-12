import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown'; // Import ReactMarkdown

/**
 * @module BiliUrlSubmitForm
 * @description A React component for submitting Bilibili video URLs to the backend API.
 * It handles user input for the URL, manages loading states, and displays session ID, status, or errors.
 */
function BiliUrlSubmitForm() {
  const [urlInput, setUrlInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const [currentStatusMessage, setCurrentStatusMessage] = useState(null);
  const [resultsData, setResultsData] = useState(null); // 新增状态来存储最终结果

  // Mapping backend status strings to user-friendly messages
  const statusDisplayMap = {
    'processing_initiated': '处理已启动...',
    'bili_processing_started': 'B站视频处理开始...',
    'bili_download_active': '下载视频中...',
    'bili_download_success': '视频下载成功。',
    'bili_audio_extraction_active': '提取音频中...',
    'bili_audio_extraction_success': '音频提取成功。',
    'bili_asr_active': '语音转文字处理中...',
    'bili_asr_success': '语音转文字完成。',
    'transcript_processing_started': '处理原始转录文本...', // For raw transcript path
    'a1_preprocessing_active': 'AI模块A.1处理中 (转录预处理)...',
    'a1_preprocessing_complete': 'AI模块A.1处理完成。',
    'a2_extraction_active': 'AI模块A.2处理中 (关键信息提取)...',
    'a2_extraction_complete': 'AI模块A.2处理完成。',
    'note_generation_active': 'AI模块B处理中 (笔记生成)...',
    'note_generation_complete': 'AI模块B处理完成。',
    'knowledge_cues_generation_active': 'AI模块D处理中 (知识提示生成)...',
    'knowledge_cues_generation_complete': 'AI模块D处理完成。',
    'all_processing_complete': '所有处理步骤成功完成。🎉',
    'error_pipeline_failed': '处理管道失败。请检查服务器日志。',
    'error_no_valid_input': '输入无效（未提供URL或转录文本）。',
    'error_bili_download_yt_dlp_failed': '视频下载失败 (yt-dlp错误)。',
    'error_bili_download_file_missing': '视频下载失败 (文件缺失)。',
    'error_audio_extraction': '音频提取失败。',
    'error_asr_misconfigured': 'ASR配置错误。',
    'error_asr_failed': 'ASR处理失败。',
    'error_in_a1_llm': 'AI模块A.1调用失败。',
    'error_in_a2_llm': 'AI模块A.2调用失败。',
    'error_in_b_llm': 'AI模块B调用失败。',
    'error_in_d_llm': 'AI模块D调用失败。',
    'error_pre_d_note_missing': '模块D所需笔记缺失。'
    // Add other statuses as needed
  };

  // Helper function to format time from seconds to HH:MM:SS or MM:SS
  const formatTime = (totalSeconds) => {
    if (typeof totalSeconds !== 'number' || totalSeconds < 0) {
      return '--:--'; // Handle invalid input
    }
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);
    let timeString = '';
    if (hours > 0) {
      timeString += `${String(hours).padStart(2, '0')}:`;
    }
    timeString += `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    return timeString;
  };

  const handleInputChange = (event) => {
    setUrlInput(event.target.value);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setSessionId(null);
    setError(null);
    setCurrentStatusMessage(null);
    setResultsData(null); // 新提交时清空结果数据

    // 使用Vite环境变量读取API基础地址，支持本地开发回退
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
    const endpoint = `${API_BASE_URL}/api/v1/learning_sessions/`;

    const body = {
      bilibili_video_url: urlInput,
      initialVideoTitle: `Bili Video from Frontend - ${new Date().toISOString()}`,
      initialSourceDescription: "Submitted via React form",
    };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch (parseError) {
          setError(`API Error: ${response.status} ${response.statusText}`);
          console.error("Error parsing API error response:", parseError);
           // Throw to be caught by the outer catch
           throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        // Handle structured validation errors (e.g., from FastAPI)
        if (errorData.detail && Array.isArray(errorData.detail) && errorData.detail.length > 0 && errorData.detail[0].msg) {
          setError(`Validation Error: ${errorData.detail[0].msg}`);
           throw new Error(`Validation Error: ${errorData.detail[0].msg}`);
        } else if (errorData.detail) { // Handle other forms of detail messages
           setError(`API Error Detail: ${errorData.detail}`);
            throw new Error(`API Error Detail: ${errorData.detail}`);
        } else if (errorData.message) {
           setError(`API Error Message: ${errorData.message}`);
            throw new Error(`API Error Message: ${errorData.message}`);
        } else {
          setError(`API Error: ${response.status} ${response.statusText}`);
           throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

      }

      const data = await response.json();
      setSessionId(data.sessionId); // Assuming backend returns { sessionId: "...", status: "..." }
      // Initial status message will be set by the useEffect hook triggered by sessionId change
      setUrlInput(''); // Optionally clear input on success

    } catch (err) {
      console.error("Fetch error:", err);
      // If error was already set by a more specific handler above, don't override
      if (!error) {
         setError(err.message || 'An unexpected error occurred during submission.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Effect for polling the status
  useEffect(() => {
    let timerId; // To store the setTimeout ID

    const fetchStatus = async () => {
      if (!sessionId) return; // Only poll if sessionId exists

      // 使用Vite环境变量读取API基础地址，支持本地开发回退
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
      const statusEndpoint = `${API_BASE_URL}/api/v1/learning_sessions/${sessionId}/status`;

      try {
        const response = await fetch(statusEndpoint);

        if (!response.ok) {
          const errorText = await response.text();
          setCurrentStatusMessage(`Error fetching status: ${response.status} ${response.statusText} - ${errorText}`);
          // Stop polling on error
          return;
        }

        const data = await response.json();
        const currentStatus = data.status;

        // Update the displayed status message
        setCurrentStatusMessage(statusDisplayMap[currentStatus] || `Unknown status: ${currentStatus}`);

        // Determine if polling should continue
        const isFinalState = currentStatus === 'all_processing_complete' || currentStatus.startsWith('error_');

        if (!isFinalState) {
          // Schedule the next poll (e.g., every 5-10 seconds)
          timerId = setTimeout(fetchStatus, 7000); // Poll every 7 seconds
        } else {
           // Processing is complete or failed, no more polling needed
           console.log(`会话 ${sessionId}: 处理完成或失败，状态为 ${currentStatus}。停止轮询。`);
           if (currentStatus === 'all_processing_complete') {
             setResultsData(data.final_results); // 设置最终结果数据
           }
           // You could add logic here to fetch/display final results if status is 'all_processing_complete'
        }

      } catch (err) {
        console.error("Polling fetch error:", err);
        setCurrentStatusMessage(`Error during status polling: ${err.message}`);
        // Stop polling on error
      }
    };

    // Start polling if sessionId is set
    if (sessionId) {
      // Set initial status message immediately before first fetch
       setCurrentStatusMessage(statusDisplayMap['processing_initiated'] || '处理已启动...');
      fetchStatus();
    } else {
       // If sessionId becomes null (e.g., new submission), clear status message and results
      setCurrentStatusMessage(null);
      setResultsData(null); // sessionId 变为 null 时清空结果数据
    }


    // Cleanup function to clear the timer if the component unmounts or sessionId changes
    return () => {
      if (timerId) {
        clearTimeout(timerId);
      }
    };
  }, [sessionId]); // Re-run effect when sessionId changes

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="biliUrl">Bilibili Video URL:</label>
          <input
            type="text"
            id="biliUrl"
            value={urlInput}
            onChange={handleInputChange}
            placeholder="e.g., https://www.bilibili.com/video/BV..."
            disabled={isLoading}
          />
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? '提交中...' : '提交'}
        </button>
      </form>

      {/* Display Session ID if available */}
      {sessionId && (
        <div style={{ marginTop: '20px', padding: '10px', border: '1px solid #ddd', backgroundColor: '#f9f9f9' }}>
          <p>提交成功！</p>
          <p>会话 ID: {sessionId}</p>
          {/* Display current status message from polling */}
          {currentStatusMessage && (
             <p>状态: {currentStatusMessage}</p>
          )}
        </div>
      )}

      {/* Display Error if an error occurred */}
      {error && (
        <div style={{ marginTop: '20px', padding: '10px', border: '1px solid red', color: 'red', backgroundColor: '#ffe6e6' }}>
          <p>发生错误:</p>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{typeof error === 'object' ? JSON.stringify(error, null, 2) : error}</pre>
        </div>
      )}

       {/* Display loading state specifically for the initial POST */}
       {isLoading && !sessionId && !error && (
           <div style={{ marginTop: '20px', padding: '10px', border: '1px solid blue', color: 'blue', backgroundColor: 'e6f3ff' }}>
               <p>正在提交 URL 并创建会话...</p>
           </div>
       )}

       {/* Display Final Results if available */}
       {resultsData && (
         <div style={{ marginTop: '20px', padding: '10px', border: '1px solid green', backgroundColor: 'e6ffe6' }}>
           {/* Display AI-generated Video Title */}
           {resultsData.ai_generated_video_title && (
             <h2 style={{ 
               textAlign: 'center', 
               marginBottom: '20px', 
               paddingBottom: '10px', 
               borderBottom: '1px solid #eee',
               fontSize: '1.5rem',
               fontWeight: '600',
               color: '#333'
             }}>
               {resultsData.ai_generated_video_title}
             </h2>
           )}

           {/* Display Note as HTML */}
           {resultsData.notes && resultsData.notes.length > 0 && resultsData.notes[0].markdown_content && (
             <div style={{ textAlign: 'left' }}>
               <h3 style={{ textAlign: 'left' }}>学习笔记</h3>
               <div className="markdown-rendered-content" style={{ textAlign: 'left', padding: '10px', border: '1px solid #eee' }}>
                 <ReactMarkdown>{resultsData.notes[0].markdown_content}</ReactMarkdown>
               </div>
             </div>
           )}

           {/* Display Knowledge Cues */}
           {resultsData.notes && resultsData.notes.length > 0 && resultsData.notes[0].knowledge_cues && resultsData.notes[0].knowledge_cues.length > 0 && (
             <div style={{ textAlign: 'left' }}>
               <h3 style={{ textAlign: 'left' }}>知识点小提示</h3>
               <div style={{ maxHeight: '300px', overflowY: 'auto', padding: '10px', border: '1px solid #eee', textAlign: 'left' }}>
                 {resultsData.notes[0].knowledge_cues.map((cue, index) => (
                   <div key={cue.cue_id || `cue-${index}`} style={{ borderBottom: '1px dashed #ccc', paddingBottom: '10px', marginBottom: '10px', textAlign: 'left' }}>
                     <p style={{ fontWeight: 'bold', marginBottom: '5px' }}>问：{cue.question_text}</p>
                     <p style={{ marginBottom: '3px' }}>答：{cue.answer_text}</p>
                     {cue.difficulty_level && <small style={{ color: '555' }}>难度：{cue.difficulty_level}</small>}
                   </div>
                 ))}
               </div>
             </div>
           )}

           {/* Display Timestamped Transcript Segments */}
           {resultsData.timestamped_transcript_segments && resultsData.timestamped_transcript_segments.length > 0 && (
             <div style={{ textAlign: 'left' }}>
               <h3 style={{ textAlign: 'left' }}>带时间戳的转录片段</h3>
               <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #eee', padding: '10px', textAlign: 'left' }}>
                 {resultsData.timestamped_transcript_segments.map((segment, index) => (
                   <div key={segment.segmentId || `segment-${index}`} style={{ marginBottom: '5px', textAlign: 'left' }}>
                     <span style={{ color: '007bff', marginRight: '10px', fontFamily: 'monospace' }}>
                       [{formatTime(segment.startTimeSeconds)}]
                     </span>
                     <span>{segment.text}</span>
                   </div>
                 ))}
               </div>
             </div>
           )}

           {/* Display Plain Text Transcript */}
           {resultsData.plain_transcript_text && (
             <div style={{ textAlign: 'left' }}>
               <h3 style={{ textAlign: 'left' }}>纯文本转录</h3>
               <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', textAlign: 'left' }}>{resultsData.plain_transcript_text}</pre>
             </div>
           )}
         </div>
       )}

    </div>
  );
}

export default BiliUrlSubmitForm;