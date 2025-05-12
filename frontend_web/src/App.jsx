import './App.css';
import TranscriptSubmitForm from './components/TranscriptSubmitForm';
import BiliUrlSubmitForm from './components/BiliUrlSubmitForm';

/**
 * @file App.jsx
 * @description Main application component.
 */
function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>AI Learning Companion</h1>
        <p>MVP - Iteration 1: Core Flow Experience Loop</p>
      </header>
      <main>
        <section className="form-section">
          <h2>Submit Raw Transcript Text</h2>
          <TranscriptSubmitForm />
        </section>
        <hr style={{ margin: '2rem 0' }} />
        <section className="form-section">
          <h2>Submit Bilibili Video URL</h2>
          <BiliUrlSubmitForm />
        </section>
      </main>
      <footer style={{ textAlign: 'center', padding: '1rem 0', marginTop: '2rem', borderTop: '1px solid #eee'}}>
        <p>&copy; {new Date().getFullYear()} AI Learning Companion MVP</p>
      </footer>
    </div>
  );
}

export default App;
