/**
 * App.jsx — BitHub Routing & State Controller
 *
 * Coordinates three views in the application:
 *   1. landing: Campus selection landing page (Jaipur / Mesra)
 *   2. subject-selector: Intermediate course selection arranged by Semester 1 & Semester 2
 *   3. subject-dashboard: Dynamic specific dashboard for active course codes or lab items
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import CampusCard from './components/CampusCard';
import Toast from './components/Toast';
import SubjectSelector from './components/SubjectSelector';
import JaipurDashboard from './components/JaipurDashboard';

/* Import campus images from the images directory */
import jaipurImg from '../images/jaipur.png';
import mesraImg from '../images/mesra.png';

function App() {
  const [view, setView] = useState('landing'); // 'landing', 'subject-selector', 'subject-dashboard'
  const [theme, setTheme] = useState('light'); // 'light', 'dark'
  const [selectedSubjectCode, setSelectedSubjectCode] = useState(null);
  
  const [toastVisible, setToastVisible] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const timerRef = useRef(null);

  /* Synchronize html theme attribute with React state */
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  /* Toggle Light / Dark Mode globally */
  const toggleTheme = useCallback(() => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  /* Show a toast notification when a disabled campus is clicked */
  const handleDisabledClick = useCallback((campusName) => {
    if (timerRef.current) clearTimeout(timerRef.current);

    setToastMessage(`${campusName} campus is coming soon!`);
    setToastVisible(true);

    timerRef.current = setTimeout(() => {
      setToastVisible(false);
    }, 2500);
  }, []);

  /* Cleanup timer on unmount */
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // PAGE VIEW ROUTER
  if (view === 'subject-dashboard' && selectedSubjectCode) {
    return (
      <JaipurDashboard 
        subjectCode={selectedSubjectCode}
        theme={theme} 
        onToggleTheme={toggleTheme} 
        onBack={() => setView('subject-selector')} 
      />
    );
  }

  if (view === 'subject-selector') {
    return (
      <SubjectSelector
        theme={theme}
        onToggleTheme={toggleTheme}
        onSelectSubject={(code) => {
          setSelectedSubjectCode(code);
          setView('subject-dashboard');
        }}
        onBackToLanding={() => setView('landing')}
      />
    );
  }

  return (
    <main className="landing-page" id="landing-page">
      
      {/* Light/Dark Toggle Switch on landing page top right */}
      <div className="landing-theme-toggle-wrapper">
        <button 
          className="theme-toggle-btn" 
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
          aria-label="Toggle theme mode"
          id="landing-theme-toggle"
        >
          {theme === 'light' ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="toggle-icon">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="toggle-icon">
              <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
            </svg>
          )}
          <span className="theme-toggle-slider">
            <span className="theme-toggle-knob" />
          </span>
        </button>
      </div>

      {/* BitHub Logo / Title */}
      <h1 className="landing-title" id="bithub-title">
        BitHub
      </h1>

      {/* Subtitle */}
      <p className="landing-subtitle" id="campus-subtitle">
        Select your campus
      </p>

      {/* Campus Cards */}
      <div className="campus-grid" id="campus-grid">
        <CampusCard
          name="JAIPUR"
          image={jaipurImg}
          href="#"
          disabled={false}
          onClick={() => setView('subject-selector')}
        />
        <CampusCard
          name="MESRA"
          image={mesraImg}
          href="../index.html"
          disabled={false}
        />
      </div>

      {/* Toast Notification */}
      <Toast message={toastMessage} visible={toastVisible} />

      {/* Footer */}
      <footer className="landing-footer" id="landing-footer">
        © 2025–2026 Birla Institute of Technology | Team BitHub
      </footer>
    </main>
  );
}

export default App;
