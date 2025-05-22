import './App.css';
// import TranscriptSubmitForm from './components/TranscriptSubmitForm'; // Removed
// import BiliUrlSubmitForm from './components/BiliUrlSubmitForm'; // Removed
import UnifiedInputForm from './components/UnifiedInputForm'; // Added

/**
 * @file App.jsx
 * @description Main application component.
 */
function App() {
  // State for results data, session ID, etc., could be lifted here in a future refactor
  // For now, UnifiedInputForm manages its own submission lifecycle and basic results display.

  return (
    <div className="App">
      <header className="App-header">
        {/* Title is now inside UnifiedInputForm, or could be here if UnifiedInputForm was purely for input */}
      </header>
      <main>
        <UnifiedInputForm />
      </main>
      <footer style={{ textAlign: 'center', padding: '1rem 0', marginTop: '2rem', borderTop: '1px solid #eee'}}>
        <p>&copy; {new Date().getFullYear()} AI Learning Companion MVP</p>
      </footer>
    </div>
  );
}

export default App;
