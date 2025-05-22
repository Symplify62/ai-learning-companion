import React, { useState, useEffect } from 'react';
import { updateNote } from '../services/apiClient';

/**
 * @module NoteEditor
 * @description A React component for editing a generated note's Markdown content.
 */
function NoteEditor({ noteId, initialMarkdownContent, onSaveSuccess, onCancel }) {
  const [markdownContent, setMarkdownContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    setMarkdownContent(initialMarkdownContent || '');
  }, [initialMarkdownContent]);

  const handleContentChange = (event) => {
    setMarkdownContent(event.target.value);
  };

  const handleSave = async () => {
    if (!noteId) {
      setError("Note ID is missing. Cannot save.");
      return;
    }
    setIsLoading(true);
    setError(null);
    setSuccessMessage('');

    try {
      const updatedNoteData = await updateNote(noteId, { markdown_content: markdownContent });
      setIsLoading(false);
      setSuccessMessage('Note saved successfully!');
      if (onSaveSuccess) {
        onSaveSuccess(updatedNoteData); // Pass the updated note data to the parent
      }
      // Optionally, clear message after a few seconds
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setIsLoading(false);
      console.error("Error updating note:", err);
      setError(err.message || 'Failed to save note. Please try again.');
      setTimeout(() => setError(null), 5000);
    }
  };

  return (
    <div style={{ border: '1px solid #ccc', padding: '15px', margin: '10px 0', borderRadius: '5px' }}>
      <h4>Edit Note (ID: {noteId})</h4>
      <textarea
        value={markdownContent}
        onChange={handleContentChange}
        rows={15}
        style={{ width: '100%', padding: '10px', marginBottom: '10px', border: '1px solid #ddd', borderRadius: '4px', minHeight: '200px', fontFamily: 'monospace' }}
        placeholder="Enter Markdown content..."
        disabled={isLoading}
      />
      <div>
        <button onClick={handleSave} disabled={isLoading} style={{ marginRight: '10px', padding: '8px 15px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          {isLoading ? 'Saving...' : 'Save Note'}
        </button>
        {onCancel && (
          <button onClick={onCancel} disabled={isLoading} style={{ padding: '8px 15px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            Cancel
          </button>
        )}
      </div>
      {error && <p style={{ color: 'red', marginTop: '10px' }}>Error: {error}</p>}
      {successMessage && <p style={{ color: 'green', marginTop: '10px' }}>{successMessage}</p>}
    </div>
  );
}

export default NoteEditor;
