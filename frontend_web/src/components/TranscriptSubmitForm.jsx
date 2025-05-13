import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getStatusDisplay } from '../utils/statusConfig'; // 导入新的状态显示工具
import styles from './TranscriptSubmitForm.module.scss'; // 导入SCSS模块

/**
 * @file TranscriptSubmitForm.jsx
 * @description A React component for submitting a transcript to initiate AI processing,
 *              polling for status, and displaying results.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

const TranscriptSubmitForm = () => {
  const [rawTranscriptText, setRawTranscriptText] = useState('');
  const [initialVideoTitle, setInitialVideoTitle] = useState('');
  const [initialSourceDescription, setInitialSourceDescription] = useState('');
  
  const [apiResponse, setApiResponse] = useState(null); // Stores initial POST response
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false); // For initial submission
  const [dataFetchingLoading, setDataFetchingLoading] = useState(false); // For fetching note/cues

  // New state variables for polling and results
  const pollingIntervalIdRef = useRef(null); // Using ref to hold interval ID for reliable clearing
  const [currentSessionStatus, setCurrentSessionStatus] = useState('');
  const [generatedNoteData, setGeneratedNoteData] = useState(null);
  const [knowledgeCuesData, setKnowledgeCuesData] = useState(null);

  // State for dynamic layout
  const [isResultsPanelVisible, setIsResultsPanelVisible] = useState(false);
  const [isProcessingNewSubmission, setIsProcessingNewSubmission] = useState(false);

  const resetUIState = (resetLayout = false) => {
    setError(null);
    setApiResponse(null);
    setCurrentSessionStatus('');
    setGeneratedNoteData(null);
    setKnowledgeCuesData(null);
    if (pollingIntervalIdRef.current) {
      clearInterval(pollingIntervalIdRef.current);
      pollingIntervalIdRef.current = null;
    }
    if (resetLayout) {
      setIsResultsPanelVisible(false);
      setIsProcessingNewSubmission(false);
    }
    // Keep form inputs as they are, or reset them too if desired
    // setRawTranscriptText('');
    // setInitialVideoTitle('');
    // setInitialSourceDescription('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    // resetUIState(); // Call resetUIState more selectively or with params
    setError(null); // Clear general errors

    if (isResultsPanelVisible) {
      // If results panel is already visible, it's a new submission while results are shown
      setIsProcessingNewSubmission(true); // Show placeholder in results panel
      setGeneratedNoteData(null);       // Clear old notes
      setKnowledgeCuesData(null);     // Clear old cues
      setCurrentSessionStatus('processing_initiated'); // Visually indicate processing starts
    } else {
      // This is the first submission, or a submission after UI was fully reset
      // Ensure data from any previous incomplete state is cleared
      setGeneratedNoteData(null);
      setKnowledgeCuesData(null);
      setIsProcessingNewSubmission(false); 
    }

    if (!rawTranscriptText.trim()) {
      setError('Raw transcript text is required.');
      return;
    }

    setLoading(true);

    const payload = {
      rawTranscriptText: rawTranscriptText,
      initial_video_title: initialVideoTitle || null,
      initial_source_description: initialSourceDescription || null,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/learning_sessions/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const responseData = await response.json();

      if (!response.ok) {
        let errorMessage = `API Error: ${response.status}`;
        if (responseData && responseData.detail) {
          if (Array.isArray(responseData.detail)) {
            errorMessage += responseData.detail.map(d => ` - ${d.loc.join('.')} - ${d.msg} (${d.type})`).join('; ');
          } else if (typeof responseData.detail === 'string') {
            errorMessage += ` - ${responseData.detail}`;
          }
        } else {
          errorMessage += ' - No error details available.';
        }
        throw new Error(errorMessage);
      }
      
      setApiResponse(responseData); // Store session_id, status, timestamp
      setCurrentSessionStatus(responseData.status);
      console.log('handleSubmit: Initial apiResponse set:', responseData); // Log 1

    } catch (err) {
      setError(err.message || 'An unexpected error occurred during submission. Please try again.');
      console.error("Submission error:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchNoteAndCues = async (sessionId) => {
    if (!sessionId) return;
    setDataFetchingLoading(true);
    setError(null); // Clear previous errors before fetching new data

    try {
      // Fetch Note
      const notesResponse = await fetch(`${API_BASE_URL}/api/v1/learning_sessions/${sessionId}/notes`);
      if (!notesResponse.ok) {
        const errorData = await notesResponse.json().catch(() => ({}));
        throw new Error(`Failed to fetch notes: ${notesResponse.status} - ${errorData.detail || 'Unknown error'}`);
      }
      const notesData = await notesResponse.json();

      if (notesData && notesData.length > 0) {
        const note = notesData[0]; // Assuming the first note is the relevant one
        setGeneratedNoteData({
          noteId: note.note_id,
          markdownContent: note.markdown_content,
          estimatedReadingTimeSeconds: note.estimated_reading_time_seconds,
          keyConceptsMentioned: note.key_concepts_mentioned,
          summaryOfNote: note.summary_of_note,
          // Add any other note fields you need from the backend response
        });

        // Fetch Knowledge Cues using the fetched note_id
        const cuesResponse = await fetch(`${API_BASE_URL}/api/v1/learning_sessions/notes/${note.note_id}/knowledge_cues`);
        if (!cuesResponse.ok) {
          const errorDataCues = await cuesResponse.json().catch(() => ({}));
          throw new Error(`Failed to fetch knowledge cues: ${cuesResponse.status} - ${errorDataCues.detail || 'Unknown error'}`);
        }
        const cuesData = await cuesResponse.json();
        setKnowledgeCuesData(cuesData);
        setIsResultsPanelVisible(true); // Show results panel after fetching
        setIsProcessingNewSubmission(false); // Done processing, hide placeholder
      } else {
        setGeneratedNoteData(null); // Or some indicator that no note was found
        setKnowledgeCuesData(null);
        setError('Processing completed, but no note was generated or found.');
        setIsProcessingNewSubmission(false); // Error occurred, stop placeholder
      }
    } catch (err) {
      console.error("Error fetching note and cues:", err);
      setError(err.message || 'An error occurred while fetching generated content.');
      // Clear potentially partial data
      setGeneratedNoteData(null);
      setKnowledgeCuesData(null);
      setIsProcessingNewSubmission(false); // Error occurred, stop placeholder
    } finally {
      setDataFetchingLoading(false);
    }
  };

  // Effect for polling session status
  useEffect(() => {
    console.log('useEffect for polling: Triggered. apiResponse:', apiResponse); // Keep this existing log

    if (!apiResponse?.sessionId || apiResponse.status !== 'processing_initiated') {
      console.log('useEffect for polling: Condition to START/CONTINUE polling NOT MET. Current apiResponse.sessionId:', apiResponse?.sessionId, 'Current apiResponse.status:', apiResponse?.status, 'Expected status "processing_initiated" to start polling, or a non-terminal status to continue. Clearing interval if any.');
      if (pollingIntervalIdRef.current) {
        console.log('useEffect for polling: Clearing interval with ID:', pollingIntervalIdRef.current);
        clearInterval(pollingIntervalIdRef.current);
        pollingIntervalIdRef.current = null;
      }
      return; 
    }
    
    console.log('useEffect for polling: Initial conditions to start polling seem met. apiResponse.sessionId:', apiResponse.sessionId, 'apiResponse.status:', apiResponse.status);
    console.log('useEffect for polling: Value of pollingIntervalIdRef.current BEFORE trying to set interval:', pollingIntervalIdRef.current);

    const checkStatus = async () => {
      console.log('checkStatus: Called. Polling for sessionId:', apiResponse?.sessionId, 'Current pollingIntervalIdRef.current:', pollingIntervalIdRef.current);
      if (!apiResponse?.sessionId || !pollingIntervalIdRef.current) { 
          console.log('checkStatus: Aborting fetch because sessionId is missing or polling was stopped.');
          if (pollingIntervalIdRef.current) {
              clearInterval(pollingIntervalIdRef.current);
              pollingIntervalIdRef.current = null;
          }
          return;
      }
      try {
        const statusResponse = await fetch(`${API_BASE_URL}/api/v1/learning_sessions/${apiResponse.sessionId}/status`);
        console.log('checkStatus: fetch call made to:', statusResponse.url, 'Status code:', statusResponse.status);

        if (!statusResponse.ok) {
          const errorDataText = await statusResponse.text(); 
          console.error(`checkStatus: Polling API error! Status: ${statusResponse.status}, Response text: ${errorDataText}`);
          setError(`Error checking status: ${statusResponse.status}. Response: ${errorDataText.substring(0,150)}. Polling stopped.`);
          clearInterval(pollingIntervalIdRef.current);
          pollingIntervalIdRef.current = null;
          return;
        }
        const statusData = await statusResponse.json(); 
        console.log('checkStatus: Fetched statusData:', statusData);
        setCurrentSessionStatus(statusData.status); 

        const terminalStatuses = ["all_processing_complete", "error_in_processing", "error_in_a1_llm", "error_in_a2_llm", "error_in_b_llm", "error_in_d_llm"];
        if (terminalStatuses.includes(statusData.status)) {
          console.log('checkStatus: Terminal status reached. Clearing interval. Status:', statusData.status, 'Polling ID Ref:', pollingIntervalIdRef.current);
          clearInterval(pollingIntervalIdRef.current);
          pollingIntervalIdRef.current = null;
          
          if (statusData.status === "all_processing_complete") {
            if (statusData.final_results && statusData.final_results.notes && statusData.final_results.notes.length > 0) {
              console.log('checkStatus: Processing complete. Found final_results in status response.');
              const firstNoteWithCues = statusData.final_results.notes[0];
              // ***** DEBUGGING NOTE CONTENT *****
              console.log('Received firstNoteWithCues from API:', JSON.stringify(firstNoteWithCues, null, 2));
              console.log('Keys in firstNoteWithCues:', Object.keys(firstNoteWithCues));
              // ***********************************
              setDataFetchingLoading(true); 
              
              setGeneratedNoteData({
                noteId: firstNoteWithCues.note_id,
                markdownContent: firstNoteWithCues.markdown_content, // Assuming 'markdown_content'
                estimatedReadingTimeSeconds: firstNoteWithCues.estimated_reading_time_seconds,
                keyConceptsMentioned: firstNoteWithCues.key_concepts_mentioned,
                summaryOfNote: firstNoteWithCues.summary_of_note,
              });
              setKnowledgeCuesData(firstNoteWithCues.knowledge_cues || []);
              setIsResultsPanelVisible(true); // Show results panel
              setIsProcessingNewSubmission(false); // Done processing new, hide placeholder
              setDataFetchingLoading(false);
            } else {
              console.log('checkStatus: Processing complete, but no final_results in status response or no notes. Falling back to fetchNoteAndCues.');
              fetchNoteAndCues(apiResponse.sessionId); 
            }
          } else {
            setError(`Processing failed with status: ${statusData.status}`);
          }
        } else {
          console.log('checkStatus: Status is still non-terminal:', statusData.status, '. Polling continues.');
        }
      } catch (err) {
        console.error("checkStatus: Polling fetch/logic error:", err);
        setError('Network error or other issue during status polling. Polling stopped.');
        if (pollingIntervalIdRef.current) {
          clearInterval(pollingIntervalIdRef.current);
          pollingIntervalIdRef.current = null;
        }
      }
    };

    if (apiResponse.status === 'processing_initiated' && !pollingIntervalIdRef.current) {
        console.log('useEffect for polling: All conditions met. Attempting to set setInterval. pollingIntervalIdRef.current is indeed null.');
        pollingIntervalIdRef.current = setInterval(checkStatus, 4000);
        console.log('useEffect for polling: setInterval CALLED. New Polling ID Ref:', pollingIntervalIdRef.current);
        checkStatus(); 
    } else {
        console.log('useEffect for polling: Did NOT set interval. apiResponse.status:', apiResponse.status, 'pollingIntervalIdRef.current:', pollingIntervalIdRef.current);
    }

    return () => {
      if (pollingIntervalIdRef.current) {
        console.log('useEffect for polling: Cleanup called. Clearing interval. Polling ID Ref:', pollingIntervalIdRef.current);
        clearInterval(pollingIntervalIdRef.current);
        pollingIntervalIdRef.current = null;
      }
    };
  }, [apiResponse]);

  const isProcessing = loading || 
                       (apiResponse && 
                        currentSessionStatus && 
                        !currentSessionStatus.startsWith('error_') && 
                        currentSessionStatus !== 'all_processing_complete') || 
                       dataFetchingLoading;

  // Helper to render status with icon and friendly text
  const renderCurrentStatus = () => {
    if (!currentSessionStatus) return null;

    const displayProps = getStatusDisplay(currentSessionStatus); // 假设 getStatusDisplay 仍然返回 { text, Icon, color (Tailwind类), isError }

    // 构建状态显示区域的 className
    let statusDisplayClassName = styles.statusDisplay;
    if (displayProps.isError) {
      statusDisplayClassName += ` ${styles.error}`; // 添加错误状态的特定类
    }

    // 构建状态文本的 className
    let statusTextClassName = styles.statusText;
    if (displayProps.isError) {
      statusTextClassName += ` ${styles.error}`;
    }

    return (
      <div className={statusDisplayClassName}>
        {displayProps.Icon && (
          <displayProps.Icon
            className={`${styles.statusIcon} ${displayProps.color || 'text-slate-600'}`} // REMOVED h-5 w-5, rely on SCSS for size
            aria-hidden="true"
          />
        )}
        <span className={statusTextClassName}>
          {displayProps.text}
        </span>
      </div>
    );
  };

  // Helper function to get the appropriate SCSS class for difficulty levels
  const getDifficultyClass = (level) => {
    if (level && typeof level === 'string') {
        const lowerLevel = level.toLowerCase(); // Normalize to lowercase
        if (lowerLevel === 'low') return styles.difficultyLow;
        if (lowerLevel === 'medium') return styles.difficultyMedium;
        if (lowerLevel === 'high') return styles.difficultyHigh;
    }
    return ''; // Default or no specific class if level is undefined or not matched
  };

  // ***** DEBUGGING NOTE CONTENT *****
  console.log('Render - generatedNoteData:', JSON.stringify(generatedNoteData, null, 2));
  if (generatedNoteData) {
    console.log('Render - generatedNoteData.markdownContent:', generatedNoteData.markdownContent);
  }
  // ***********************************

  return (
    // Main page container - class will change based on layout mode
    <div className={`${styles.pageContainer} ${isResultsPanelVisible ? styles.resultsVisibleLayout : styles.initialLayout}`}>
      
      {/* Left Panel: Input Form */}
      <div className={`${styles.inputPanel} ${isResultsPanelVisible ? styles.inputPanelSidebar : styles.inputPanelInitial}`}>
        <h1 className={`${styles.pageTitle} ${isResultsPanelVisible ? styles.leftAligned : ''}`}>AI Learning Companion</h1>
        
        {/* Scrollable Form Wrapper */}
        <div className={styles.scrollableFormWrapper}>
          <h2 className={`${styles.formTitle} ${isResultsPanelVisible ? styles.leftAligned : ''}`}>AI 学习内容处理</h2>
          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.formGroup}>
              <label htmlFor="rawTranscriptText" className={styles.formLabel}>原始学习内容 (文本转录稿):</label>
              <textarea
                id="rawTranscriptText"
                value={rawTranscriptText}
                onChange={(e) => setRawTranscriptText(e.target.value)}
                placeholder="在此粘贴带时间戳的文本转录稿..."
                rows="10"
                required
                className={styles.formTextarea}
                disabled={isProcessing}
              />
            </div>
            <div className={styles.formGroup}>
              <label htmlFor="initialVideoTitle" className={styles.formLabel}>内容标题 (可选):</label>
              <input
                type="text"
                id="initialVideoTitle"
                value={initialVideoTitle}
                onChange={(e) => setInitialVideoTitle(e.target.value)}
                placeholder="例如：量子物理入门 第1讲"
                className={styles.formInput}
                disabled={isProcessing}
              />
            </div>
            <div className={styles.formGroup}>
              <label htmlFor="initialSourceDescription" className={styles.formLabel}>来源描述 (可选):</label>
              <input
                type="text"
                id="initialSourceDescription"
                value={initialSourceDescription}
                onChange={(e) => setInitialSourceDescription(e.target.value)}
                placeholder="例如：Coursera公开课，授课教师Dr. Quantum"
                className={styles.formInput}
                disabled={isProcessing}
              />
            </div>
            <div className={styles.buttonContainer}>
              <button 
                type="submit" 
                disabled={loading || isProcessing}
                className={styles.submitButton}
              >
                {loading || isProcessing ? '正在处理中...' : '开始智能处理'}
              </button>
            </div>
          </form>
        </div> {/* End of scrollableFormWrapper */}
        
        {/* Status display: always shown below the form if currentSessionStatus has a value */}
        {currentSessionStatus && renderCurrentStatus()}
      </div> {/* End of inputPanel */}

      {/* Right Panel: Results or Placeholder - Conditionally rendered and styled */}
      {isResultsPanelVisible && (
        <div className={styles.resultsPanel}>
          {isProcessingNewSubmission ? (
            <div className={styles.processingPlaceholder}> {/* Placeholder when reprocessing */}
              {/* Placeholder content will go here - Part 4 */}
              <p>AI正在努力处理您的新请求...</p> {/* Simple text placeholder for now */}
              {/* Status is already shown in inputPanel, so not strictly needed here unless desired for emphasis */}
            </div>
          ) : (
            <> {/* Actual results: status, notes, cues */}
              {error && (
                <div className={`${styles.errorBox} mt-6 p-4 border border-red-300 rounded-md bg-red-50 text-red-700 shadow`}>
                  <p className="font-bold">错误提示:</p>
                  <p>{error}</p>
                </div>
              )}

              {dataFetchingLoading && !isProcessingNewSubmission && ( // Show loading only if not already showing new submission placeholder
                <div className="mt-6 text-center">
                  <p>正在加载学习笔记和提示...</p>
                </div>
              )}

              {/* Results Section Container for Notes and Cues */}
              {(generatedNoteData || (knowledgeCuesData && knowledgeCuesData.length > 0)) && (
                <div className={styles.resultsContentContainer}> {/* Renamed from resultsContainer to avoid conflict with SCSS module class if any */} 
                  {generatedNoteData && (
                    <div className={styles.notesSection}>
                      <h3 className={styles.notesTitle}>学习笔记 (AI生成)</h3>
                      <div className={styles.markdownContentArea}>
                        {typeof generatedNoteData.markdownContent === 'string' ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {generatedNoteData.markdownContent}
                          </ReactMarkdown>
                        ) : (
                          <p className={styles.errorMessage}>Error: Note content is not in a displayable format.</p>
                        )}
                      </div>
                      {generatedNoteData.summary_of_note && (
                        <div className={`${styles.metadataBox} mb-4 p-3 bg-indigo-50 rounded-md border border-indigo-200`}>
                          <h4 className={`${styles.metadataTitle} text-sm font-semibold text-indigo-700`}>笔记摘要:</h4>
                          <p className="text-sm text-indigo-600italic">{generatedNoteData.summary_of_note}</p>
                        </div>
                      )}
                      {generatedNoteData.key_concepts_mentioned && generatedNoteData.key_concepts_mentioned.length > 0 && (
                        <div className={styles.metadataBox}>
                          <h4 className={styles.metadataTitle}>核心概念:</h4>
                          <div className="flex flex-wrap gap-2 mt-1">
                            {generatedNoteData.key_concepts_mentioned.map((concept, index) => (
                              <span key={index} className={`${styles.conceptTag} px-2 py-1 bg-slate-200 text-slate-700 rounded-full text-xs font-medium`}>
                                {concept}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {generatedNoteData.estimated_reading_time_seconds && (
                        <p className={`${styles.metadataText} text-xs text-slate-500 mb-3`}>预计阅读时长: {Math.ceil(generatedNoteData.estimated_reading_time_seconds / 60)} 分钟</p>
                      )}
                    </div>
                  )}

                  {knowledgeCuesData && knowledgeCuesData.length > 0 && (
                    <div className={styles.knowledgeCuesSection}>
                      <h3 className={styles.cuesTitle}>知识点提示 (AI生成)</h3>
                      <ul className={styles.cueList}>
                        {knowledgeCuesData.map((cue, index) => (
                          <li key={cue.cue_id || index} className={styles.cueItem}>
                            <p><strong>问题 {index + 1}:</strong> {cue.question_text}</p>
                            <p><strong>答案:</strong> {cue.answer_text}</p>
                            <div className={styles.cueDetails}>
                              <span 
                                className={`${styles.difficulty} ${getDifficultyClass(cue.difficulty_level)}`}>
                                难度: {cue.difficulty_level} 
                              </span>
                              {cue.source_reference_in_note && (
                                <span className={styles.sourceReference}>笔记参考: {cue.source_reference_in_note}</span>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

// Enhanced styling object
const inlineStyles = {
  container: {
    maxWidth: '900px',
    margin: '2rem auto',
    padding: '2rem',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    backgroundColor: '#fcfcfc',
    borderRadius: '12px',
    boxShadow: '0 6px 18px rgba(0, 0, 0, 0.07)',
    color: '#333',
  },
  title: {
    textAlign: 'center',
    color: '#1a2c47',
    marginBottom: '2.5rem',
    fontSize: '2.4rem',
    fontWeight: '600',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.8rem',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
  },
  label: {
    marginBottom: '0.6rem',
    fontWeight: '500',
    fontSize: '1rem',
    color: '#34495e',
  },
  requiredIndicator: {
    color: '#d9534f',
    marginLeft: '0.25rem',
  },
  input: {
    padding: '0.85rem 1.1rem',
    border: '1px solid #ccc',
    borderRadius: '6px',
    fontSize: '1rem',
    backgroundColor: '#fff',
    transition: 'border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
  },
  textarea: {
    padding: '0.85rem 1.1rem',
    border: '1px solid #ccc',
    borderRadius: '6px',
    fontSize: '1rem',
    backgroundColor: '#fff',
    minHeight: '180px',
    resize: 'vertical',
    transition: 'border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
    lineHeight: '1.6',
  },
  submitButton: {
    padding: '0.9rem 1.8rem',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '1.15rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s ease-in-out, transform 0.1s ease',
    marginTop: '1.2rem',
    alignSelf: 'center',
    minWidth: '200px',
  },
  statusText: {
    textAlign: 'center',
    marginTop: '1.5rem',
    color: '#5bc0de',
    fontSize: '1.1rem',
    fontWeight: '500',
  },
  loadingText: {
    textAlign: 'center',
    marginTop: '1.5rem',
    color: '#007bff',
    fontSize: '1.1rem',
  },
  errorBox: {
    marginTop: '2rem',
    padding: '1.2rem',
    backgroundColor: '#f8d7da',
    border: '1px solid #f5c6cb',
    borderRadius: '6px',
    color: '#721c24',
  },
  errorText: {
    margin: 0,
    whiteSpace: 'pre-wrap',
    lineHeight: '1.5',
  },
  responseBoxSlim: {
    marginTop: '1.5rem',
    padding: '0.8rem 1.2rem',
    backgroundColor: '#e6f7ff',
    border: '1px solid #91d5ff',
    borderRadius: '6px',
    fontSize: '0.95rem',
  },
  resultsSection: {
    marginTop: '2.5rem',
    padding: '1.5rem',
    backgroundColor: '#fff',
    border: '1px solid #e9ecef',
    borderRadius: '8px',
  },
  sectionTitle: {
    color: '#1a2c47',
    fontSize: '1.5rem',
    marginBottom: '1rem',
    borderBottom: '2px solid #007bff',
    paddingBottom: '0.5rem',
  },
  subSectionTitle: {
    color: '#343a40',
    fontSize: '1.2rem',
    marginTop: '1.5rem',
    marginBottom: '0.75rem',
  },
  noteMetadata: {
    marginBottom: '1.5rem',
    paddingLeft: '1rem',
    borderLeft: '3px solid #007bff',
    backgroundColor: '#f8f9fa',
    padding: '1rem',
    borderRadius: '4px',
  },
  markdownDisplayArea: {
    padding: '1rem',
    backgroundColor: '#fdfdfd',
    border: '1px solid #eee',
    borderRadius: '6px',
    lineHeight: '1.7',
    maxHeight: '500px',
    overflowY: 'auto',
  },
  cueItem: {
    padding: '1rem',
    border: '1px solid #dee2e6',
    borderRadius: '6px',
    marginBottom: '1rem',
    backgroundColor: '#f8f9fa',
  },
  // Styles for ReactMarkdown rendered elements (add more as needed)
  // These are just placeholders; proper styling would use CSS classes and a separate CSS file.
  'markdownDisplayArea h1': { fontSize: '1.8em', marginTop: '1em', marginBottom: '0.5em' },
  'markdownDisplayArea h2': { fontSize: '1.5em', marginTop: '0.8em', marginBottom: '0.4em' },
  'markdownDisplayArea p': { marginBottom: '0.8em' },
  'markdownDisplayArea ul': { paddingLeft: '2em' },
  'markdownDisplayArea ol': { paddingLeft: '2em' },
  'markdownDisplayArea blockquote': { borderLeft: '4px solid #ccc', paddingLeft: '1em', marginLeft: 0, fontStyle: 'italic' },
  'markdownDisplayArea pre': { backgroundColor: '#eee', padding: '0.8em', borderRadius: '4px', overflowX: 'auto' }, 
};


const addFocusAndMarkdownStyles = () => {
  let styleSheet = document.getElementById('dynamic-styles');
  if (!styleSheet) {
    styleSheet = document.createElement("style");
    styleSheet.id = 'dynamic-styles';
    styleSheet.type = "text/css";
    document.head.appendChild(styleSheet);
  }
  
  // It's hard to target pseudo-classes and complex selectors for markdown with inline style objects.
  // A dedicated CSS file or CSS-in-JS is better for markdown styling.
  // For now, we'll keep it simple.
  styleSheet.innerText = `
    input[type="text"]:focus, textarea:focus {
      outline: none;
      border-color: #007bff;
      box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.2);
    }
    button[type="submit"]:hover:not(:disabled) {
      background-color: #0056b3;
      transform: translateY(-1px);
    }
    button[type="submit"]:disabled {
      background-color: #aecbed;
      cursor: not-allowed;
      transform: translateY(0px);
    }
    .markdown-display-area h1 { font-size: 1.8em; margin-top: 1em; margin-bottom: 0.5em; color: #1a2c47; }
    .markdown-display-area h2 { font-size: 1.5em; margin-top: 0.8em; margin-bottom: 0.4em; color: #1a2c47; }
    .markdown-display-area h3 { font-size: 1.3em; margin-top: 0.7em; margin-bottom: 0.3em; color: #1a2c47; }
    .markdown-display-area p { margin-bottom: 0.8em; line-height: 1.7; }
    .markdown-display-area ul, .markdown-display-area ol { padding-left: 2em; margin-bottom: 1em; }
    .markdown-display-area li { margin-bottom: 0.4em; }
    .markdown-display-area blockquote { border-left: 4px solid #007bff; padding-left: 1em; margin-left: 0; font-style: italic; color: #555; background-color: #f8f9fa; padding-top: 0.5em; padding-bottom: 0.5em;}
    .markdown-display-area pre { background-color: #f0f0f0; padding: 1em; border-radius: 4px; overflow-x: auto; font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 0.9em; }
    .markdown-display-area code { background-color: #f0f0f0; padding: 0.2em 0.4em; margin: 0; font-size: 0.9em; border-radius: 3px; }
    .markdown-display-area pre code { background-color: transparent; padding: 0; margin: 0; font-size: inherit; border-radius: 0; }
    .markdown-display-area table { border-collapse: collapse; margin-bottom: 1em; width: auto; }
    .markdown-display-area th, .markdown-display-area td { border: 1px solid #ddd; padding: 0.5em 0.8em; text-align: left; }
    .markdown-display-area th { background-color: #f2f2f2; font-weight: bold; }
  `;
};
addFocusAndMarkdownStyles();

export default TranscriptSubmitForm; 