import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { createLearningSession, getLearningSessionStatus } from '../services/apiClient';
import { getStatusDisplay } from '../utils/statusConfig';
import NoteEditor from './NoteEditor'; // Assuming NoteEditor might be used in results display later
import styles from './UnifiedInputForm.module.scss'; // Create a new SCSS module or reuse/adapt existing

const UnifiedInputForm = () => {
  // Input selection
  const [inputType, setInputType] = useState('url'); // 'url' or 'text'

  // Form fields
  const [urlInput, setUrlInput] = useState('');
  const [rawTextInput, setRawTextInput] = useState('');
  const [textSubtype, setTextSubtype] = useState('timestamped_text'); // 'timestamped_text' or 'plain_text'
  const [learningObjectives, setLearningObjectives] = useState('');
  const [initialVideoTitle, setInitialVideoTitle] = useState(''); // Optional title for text inputs

  // Submission & Polling State (similar to TranscriptSubmitForm)
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [currentSessionStatus, setCurrentSessionStatus] = useState('');
  const [resultsData, setResultsData] = useState(null); // To store final results for display
  const [activeTab, setActiveTab] = useState('overview'); // State for active tab
  const [transcriptCopied, setTranscriptCopied] = useState(false);
  const [noteCopied, setNoteCopied] = useState(false);
  
  const pollingIntervalIdRef = useRef(null);


  // --- Handler for input type change ---
  const handleInputTypeChange = (event) => {
    setInputType(event.target.value);
    // Reset fields when changing type to avoid sending mixed data
    setUrlInput('');
    setRawTextInput('');
    setTextSubtype('timestamped_text');
    setLearningObjectives('');
    setInitialVideoTitle('');
    setError(null);
    setSessionId(null); // Clear session and results when input type changes
    setCurrentSessionStatus('');
    setResultsData(null);
  };

  // --- Submit Handler ---
  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setSessionId(null);
    setCurrentSessionStatus('');
    setResultsData(null);

    let payload = {
      initialVideoTitle: '',
      initialSourceDescription: "Submitted via Unified Frontend Form", // Generic description
      learning_objectives: learningObjectives || null,
    };

    if (inputType === 'url') {
      if (!urlInput.trim()) {
        setError('Bilibili Video URL is required.');
        setIsLoading(false);
        return;
      }
      payload.bilibili_video_url = urlInput;
      payload.source_type = 'url'; // Explicitly set for clarity, though model validator handles it
      payload.initialVideoTitle = `Bili Video from URL - ${new Date().toISOString()}`;
    } else { // inputType === 'text'
      if (!rawTextInput.trim()) {
        setError('Text input is required.');
        setIsLoading(false);
        return;
      }
      payload.rawTranscriptText = rawTextInput;
      payload.source_type = textSubtype;
      payload.initialVideoTitle = initialVideoTitle || `Text Input - ${textSubtype} - ${new Date().toISOString()}`;
    }

    try {
      const initialApiResponse = await createLearningSession(payload);
      setSessionId(initialApiResponse.sessionId);
      setCurrentSessionStatus(initialApiResponse.status || 'processing_initiated');
      // Clear form fields on successful submission start
      if (inputType === 'url') setUrlInput('');
      else {
        setRawTextInput('');
        setInitialVideoTitle('');
      }
      setLearningObjectives('');

    } catch (err) {
      console.error("Submission error:", err);
      let displayError = 'An unexpected error occurred during submission.';
      if (err.data && err.data.detail) {
        const detailMsg = Array.isArray(err.data.detail) 
          ? err.data.detail.map(d => (d.loc ? `${d.loc.join('.')} - ${d.msg}` : d.msg) || JSON.stringify(d)).join('; ') 
          : String(err.data.detail);
        displayError = `API Error: ${detailMsg}`;
      } else if (err.message) {
        displayError = err.message;
      }
      setError(displayError);
    } finally {
      setIsLoading(false);
    }
  };

  // --- useEffect for Polling Status ---
  useEffect(() => {
    if (!sessionId || !currentSessionStatus) {
      if (pollingIntervalIdRef.current) {
        clearInterval(pollingIntervalIdRef.current);
        pollingIntervalIdRef.current = null;
      }
      return;
    }
    
    // Don't poll if status is already terminal or if a poll is already active
    const terminalStatuses = ["all_processing_complete", "error_pipeline_failed", "error_no_valid_input"]; // Add other error states
    if (terminalStatuses.includes(currentSessionStatus) || pollingIntervalIdRef.current) {
      if (pollingIntervalIdRef.current && terminalStatuses.includes(currentSessionStatus)) {
         clearInterval(pollingIntervalIdRef.current);
         pollingIntervalIdRef.current = null;
      }
      // If processing is complete, fetch final results if not already present in statusData
      if (currentSessionStatus === "all_processing_complete" && resultsData && !resultsData.notes) { // Check if notes are missing
        // This logic might need refinement based on what getLearningSessionStatus returns
        // For now, assuming resultsData from status might be sufficient or App.jsx handles fetching full results.
        console.log("Polling stopped, processing complete. Results might need full fetch via App.jsx");
      }
      return;
    }

    const checkStatus = async () => {
      try {
        const statusData = await getLearningSessionStatus(sessionId);
        setCurrentSessionStatus(statusData.status);
        
        // If statusData contains final_results, set them
        if (statusData.final_results) {
          setResultsData(statusData.final_results);
          // If terminal status with results, clear interval
           if (statusData.status === "all_processing_complete" || statusData.status.startsWith("error_")) {
             clearInterval(pollingIntervalIdRef.current);
             pollingIntervalIdRef.current = null;
           }
        } else if (statusData.status === "all_processing_complete" && !statusData.final_results) {
            // Handle case where processing is complete but results are not in status payload
            // This might involve a separate call from a parent component or here.
            // For now, we just stop polling. Parent component can fetch full results.
            console.log("Processing complete, but full results not in status. Parent should fetch.");
            clearInterval(pollingIntervalIdRef.current);
            pollingIntervalIdRef.current = null;
        }


      } catch (err) {
        console.error("Polling error:", err);
        setError("Error fetching status. Polling stopped.");
        clearInterval(pollingIntervalIdRef.current);
        pollingIntervalIdRef.current = null;
      }
    };

    if (currentSessionStatus === 'processing_initiated' || 
        (currentSessionStatus && !currentSessionStatus.startsWith('error_') && currentSessionStatus !== 'all_processing_complete')) {
      pollingIntervalIdRef.current = setInterval(checkStatus, 5000); // Poll every 5 seconds
      checkStatus(); // Initial check
    }

    return () => {
      if (pollingIntervalIdRef.current) {
        clearInterval(pollingIntervalIdRef.current);
        pollingIntervalIdRef.current = null;
      }
    };
  }, [sessionId, currentSessionStatus, resultsData]); // Added resultsData to dependencies to avoid re-polling if results are already fetched

  // --- Render Current Status Display ---
  const renderCurrentStatusDisplay = () => {
    let content = null;
    let showSpinner = false;
    let containerClass = styles.statusDisplay; // Default class

    const isMidProcessing = currentSessionStatus && 
                            !currentSessionStatus.startsWith('error_') && 
                            currentSessionStatus !== 'all_processing_complete';

    if (error) {
      content = `错误: ${error}`;
      containerClass = `${styles.statusDisplay} ${styles.statusError}`; // Use statusDisplay as base for consistent padding/margin
    } else if (isLoading && !sessionId) {
      content = "正在提交，请稍候...";
      showSpinner = true;
      containerClass = `${styles.statusDisplay} ${styles.statusLoading}`;
    } else if (sessionId) { // If there's a session ID, we always show some status
      const display = getStatusDisplay(currentSessionStatus || 'processing_initiated');
      content = display.text;
      if (display.Icon) {
        content = ( // Ensure Icon is part of the span or handled with flex for alignment
          <> 
            <display.Icon className={styles.statusIcon} aria-hidden="true" />
            <span>{display.text}</span>
          </>
        );
      }
      showSpinner = isMidProcessing && !display.isError;
      if(display.isError) {
        containerClass = `${styles.statusDisplay} ${styles.statusError}`;
      } else if (isMidProcessing || currentSessionStatus === 'processing_initiated') {
         containerClass = `${styles.statusDisplay} ${styles.statusInProgress}`; // A general in-progress style
      } else if (currentSessionStatus === 'all_processing_complete'){
         containerClass = `${styles.statusDisplay} ${styles.statusSuccess}`; // A general success style
      }
    }

    if (content === null) return null; // Don't render anything if no conditions met

    return (
      <div className={containerClass}>
        {content}
        {showSpinner && <div className={styles.spinner}></div>}
      </div>
    );
  };

  const handleCopyToClipboard = async (textToCopy, type) => {
    if (!navigator.clipboard) {
      // Fallback for older browsers or insecure contexts (though unlikely for modern dev)
      setError('Clipboard API not available. Please copy manually.');
      setTimeout(() => setError(null), 3000);
      return;
    }
    try {
      await navigator.clipboard.writeText(textToCopy);
      if (type === 'transcript') {
        setTranscriptCopied(true);
        setTimeout(() => setTranscriptCopied(false), 2000);
      } else if (type === 'note') {
        setNoteCopied(true);
        setTimeout(() => setNoteCopied(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
      setError('Failed to copy to clipboard. Please copy manually.');
      setTimeout(() => setError(null), 3000);
    }
  };

  return (
    <div className={styles.unifiedFormContainer}>
      <h1 className={styles.pageTitle}>AI Learning Companion</h1>
      <div className={styles.inputTypeSelector}>
        <label>
          <input type="radio" value="url" checked={inputType === 'url'} onChange={handleInputTypeChange} />
          Bilibili Video URL
        </label>
        <label>
          <input type="radio" value="text" checked={inputType === 'text'} onChange={handleInputTypeChange} />
          Text Input
        </label>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>
        {inputType === 'url' && (
          <div className={styles.formGroup}>
            <label htmlFor="biliUrl" className={styles.formLabel}>Bilibili Video URL:</label>
            <input
              type="text"
              id="biliUrl"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="e.g., https://www.bilibili.com/video/BV..."
              className={styles.formInput}
              disabled={isLoading}
            />
          </div>
        )}

        {inputType === 'text' && (
          <>
            <div className={styles.formGroup}>
              <label htmlFor="rawTextInput" className={styles.formLabel}>学习内容:</label>
              <textarea
                id="rawTextInput"
                value={rawTextInput}
                onChange={(e) => setRawTextInput(e.target.value)}
                placeholder={
                  textSubtype === 'timestamped_text'
                    ? "在此粘贴带时间戳的文本转录稿..."
                    : "在此粘贴纯文本内容..."
                }
                rows="10"
                className={styles.formTextarea}
                disabled={isLoading}
              />
            </div>
            <div className={styles.formGroup}>
              <label htmlFor="textSubtype" className={styles.formLabel}>文本类型:</label>
              <select
                id="textSubtype"
                value={textSubtype}
                onChange={(e) => setTextSubtype(e.target.value)}
                className={styles.formSelect}
                disabled={isLoading}
              >
                <option value="timestamped_text">带时间戳的文本</option>
                <option value="plain_text">纯文本 (无时间戳)</option>
              </select>
            </div>
             <div className={styles.formGroup}>
              <label htmlFor="initialVideoTitle" className={styles.formLabel}>内容标题 (可选):</label>
              <input
                type="text"
                id="initialVideoTitle"
                value={initialVideoTitle}
                onChange={(e) => setInitialVideoTitle(e.target.value)}
                placeholder="例如：我的学习笔记标题"
                className={styles.formInput}
                disabled={isLoading}
              />
            </div>
          </>
        )}
        
        {/* Common fields for all types */}
        <div className={styles.formGroup}>
            <label htmlFor="learningObjectives" className={styles.formLabel}>学习目标或重点 (可选):</label>
            <textarea
            id="learningObjectives"
            value={learningObjectives}
            onChange={(e) => setLearningObjectives(e.target.value)}
            placeholder="例如：理解视频/文本中的关键概念..."
            rows="3"
            className={styles.formTextarea}
            disabled={isLoading}
            />
        </div>

        <div className={styles.buttonContainer}>
          <button type="submit" disabled={isLoading} className={styles.submitButton}>
            {isLoading ? '处理中...' : '开始智能处理'}
          </button>
        </div>
      </form>

      {/* Status and Session ID Display */}
      {sessionId && <p style={{textAlign: 'center', fontWeight: 'bold'}}>会话 ID: {sessionId}</p>}
      {renderCurrentStatusDisplay()}

      {/* Tabbed Results Display Area */}
      {resultsData && !isLoading && currentSessionStatus === 'all_processing_complete' && (
        <div className={styles.resultsPanel}>
          <div className={styles.tabNav}>
            <button 
              className={`${styles.tabButton} ${activeTab === 'overview' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              概览与优化稿
            </button>
            <button 
              className={`${styles.tabButton} ${activeTab === 'notes' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('notes')}
              disabled={!resultsData.notes || resultsData.notes.length === 0}
            >
              学习笔记
            </button>
            <button 
              className={`${styles.tabButton} ${activeTab === 'cues' ? styles.activeTab : ''}`}
              onClick={() => setActiveTab('cues')}
              disabled={!resultsData.notes || resultsData.notes.length === 0 || !resultsData.notes[0].knowledge_cues || resultsData.notes[0].knowledge_cues.length === 0}
            >
              知识点提示
            </button>
          </div>

          <div className={styles.tabContent}>
            {/* Overview & Optimized Transcript Tab */}
            {activeTab === 'overview' && (
              <div className={styles.tabPanel}>
                {resultsData.ai_generated_video_title && (
                  <h2 className={styles.resultsVideoTitle} style={{ marginTop: '0.5em', marginBottom: '1em'}}>
                    {resultsData.ai_generated_video_title}
                  </h2>
                )}
                {resultsData.timestamped_transcript_segments && resultsData.timestamped_transcript_segments.length > 0 ? (
                  <div className={styles.transcriptSection}>
                    <div style={{display: 'flex', alignItems: 'center', marginBottom: '10px'}}>
                      <h4 className={styles.transcriptTitle} style={{margin: 0}}>AI优化稿 (分段)</h4>
                      <button 
                        onClick={() => handleCopyToClipboard(resultsData.timestamped_transcript_segments.map(s => `[${new Date(s.startTimeSeconds * 1000).toISOString().substr(14, 5)}] ${s.text}`).join('\n'))}
                        className={styles.copyButton}
                        disabled={transcriptCopied}
                      >
                        {transcriptCopied ? '已复制!' : '复制分段稿'}
                      </button>
                      {transcriptCopied && <span className={styles.copyFeedback}>Copied!</span>}
                    </div>
                    <div className={styles.transcriptSegmentsArea}>
                      {resultsData.timestamped_transcript_segments.map((segment, index) => (
                        <div key={segment.segmentId || `segment-${index}`} className={styles.transcriptSegment}>
                          {typeof segment.startTimeSeconds === 'number' && (
                            <span className={styles.timestamp}>
                              [{new Date(segment.startTimeSeconds * 1000).toISOString().substr(14, 5)}]
                            </span>
                          )}
                          <span>{segment.text}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : resultsData.plain_transcript_text ? (
                  <div className={styles.transcriptSection}>
                     <div style={{display: 'flex', alignItems: 'center', marginBottom: '10px'}}>
                        <h4 className={styles.transcriptTitle} style={{margin: 0}}>文本内容</h4>
                        <button 
                          onClick={() => handleCopyToClipboard(resultsData.plain_transcript_text)}
                          className={styles.copyButton}
                          disabled={transcriptCopied}
                        >
                          {transcriptCopied ? '已复制!' : '复制文本'}
                        </button>
                        {transcriptCopied && <span className={styles.copyFeedback}>Copied!</span>}
                      </div>
                    <pre className={styles.plainTranscriptArea}>{resultsData.plain_transcript_text}</pre>
                  </div>
                ) : (
                  <p className={styles.emptyTabMessage}>处理完成后，AI优化稿将在此处显示。</p>
                )}
              </div>
            )}

            {/* Learning Notes Tab */}
            {activeTab === 'notes' && resultsData.notes && resultsData.notes.length > 0 && (
              <div className={styles.tabPanel}>
                <div className={styles.notesSection}>
                  <div style={{display: 'flex', alignItems: 'center', marginBottom: '10px'}}>
                    {/* Edit button placeholder can go here if needed, managed by App.jsx state */}
                    <h4 className={styles.notesTitle} style={{margin: '0', flexGrow: 1}}>学习笔记内容</h4>
                     <button 
                        onClick={() => handleCopyToClipboard(resultsData.notes[0].markdown_content)}
                        className={styles.copyButton}
                        disabled={noteCopied}
                      >
                        {noteCopied ? '已复制!' : '复制笔记'}
                      </button>
                      {noteCopied && <span className={styles.copyFeedback}>Copied!</span>}
                  </div>
                  <div className={styles.markdownContentArea}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {resultsData.notes[0].markdown_content}
                    </ReactMarkdown>
                  </div>
                  {resultsData.notes[0].is_user_edited && (
                    <p className={styles.editedIndicator}>
                      (用户已编辑{resultsData.notes[0].last_edited_at ? ` - ${new Date(resultsData.notes[0].last_edited_at).toLocaleString()}` : ''})
                    </p>
                  )}
                   {resultsData.notes[0].summary_of_note && (
                    <div className={`${styles.metadataBox} mb-4 p-3`}>
                      <h4 className={styles.metadataTitle}>笔记摘要:</h4>
                      <p>{resultsData.notes[0].summary_of_note}</p>
                    </div>
                  )}
                  {resultsData.notes[0].key_concepts_mentioned && resultsData.notes[0].key_concepts_mentioned.length > 0 && (
                    <div className={styles.metadataBox}>
                      <h4 className={styles.metadataTitle}>核心概念:</h4>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {resultsData.notes[0].key_concepts_mentioned.map((concept, index) => (
                          <span key={index} className={styles.conceptTag}>
                            {concept}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {typeof resultsData.notes[0].estimated_reading_time_seconds === 'number' && (
                    <p className={styles.metadataText}>
                      预计阅读时长: {Math.ceil(resultsData.notes[0].estimated_reading_time_seconds / 60)} 分钟
                    </p>
                  )}
                </div>
              </div>
            )}
            {activeTab === 'notes' && (!resultsData.notes || resultsData.notes.length === 0) && (
                <p className={styles.emptyTabMessage}>学习笔记生成后将在此处显示。</p>
            )}


            {/* Knowledge Cues Tab */}
            {activeTab === 'cues' && resultsData.notes && resultsData.notes.length > 0 && resultsData.notes[0].knowledge_cues && resultsData.notes[0].knowledge_cues.length > 0 && (
              <div className={styles.tabPanel}>
                <div className={styles.knowledgeCuesSection}>
                   <h4 className={styles.cuesTitle} style={{margin: '0 0 10px 0', flexGrow: 1}}>知识点提示</h4>
                  <ul className={styles.cueList}>
                    {resultsData.notes[0].knowledge_cues.map((cue, index) => (
                      <li key={cue.cue_id || `cue-${index}`} className={styles.cueItem}>
                        <p><strong>问题 {index + 1}:</strong> {cue.question_text}</p>
                        <p><strong>答案:</strong> {cue.answer_text}</p>
                        {cue.difficulty_level && (
                          <div className={styles.cueDetails}>
                            <span className={`${styles.difficulty} ${styles['difficulty' + cue.difficulty_level.charAt(0).toUpperCase() + cue.difficulty_level.slice(1).toLowerCase()] || ''}`}>
                                难度: {cue.difficulty_level}
                            </span>
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
             {activeTab === 'cues' && (!resultsData.notes || resultsData.notes.length === 0 || !resultsData.notes[0].knowledge_cues || resultsData.notes[0].knowledge_cues.length === 0) && (
                <p className={styles.emptyTabMessage}>知识点提示生成后将在此处显示。</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default UnifiedInputForm;
