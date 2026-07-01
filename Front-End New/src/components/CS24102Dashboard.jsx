import React, { useState, useEffect } from 'react';
import OnlineJudge from './OnlineJudge';
import './LabDashboard.css';

const CS24102Dashboard = ({ theme, onBack }) => {
  const [problems, setProblems] = useState([]);
  const [selectedProblem, setSelectedProblem] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/cs-problems')
      .then(res => res.json())
      .then(data => {
        setProblems(data.problems || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load problems:", err);
        setLoading(false);
      });
  }, []);

  if (selectedProblem) {
    return (
      <OnlineJudge 
        problem={selectedProblem} 
        theme={theme} 
        onBack={() => setSelectedProblem(null)} 
      />
    );
  }

  return (
    <div style={{ width: '100%', maxWidth: '1000px', margin: '0 auto' }}>
      <section className="dashboard-card" style={{marginTop: '2rem'}}>
        <div className="card-header">
          <div className="card-header-titles">
            <h3 className="card-title-main">C Lab Assignments</h3>
            <p className="card-title-sub">Select a problem to open the Online Judge</p>
          </div>
        </div>
        
        {loading ? (
          <div style={{padding: '2rem', textAlign: 'center', color: 'var(--dash-text-color)'}}>Loading problems...</div>
        ) : problems.length === 0 ? (
          <div style={{padding: '2rem', textAlign: 'center', color: 'var(--dash-text-color)'}}>No problems found.</div>
        ) : (
          <div className="subjects-button-list" style={{display: 'flex', flexDirection: 'column', gap: '1rem', padding: '0 1.5rem 1.5rem'}}>
            {problems.map(prob => (
              <button 
                key={prob.problem_id}
                className="subject-selection-btn"
                onClick={() => setSelectedProblem(prob)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
                  <div className="card-header-icon-wrapper circle-pink" style={{flexShrink: 0}}>
                    <svg className="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <polyline points="16 18 22 12 16 6"></polyline>
                      <polyline points="8 6 2 12 8 18"></polyline>
                    </svg>
                  </div>
                  <div className="btn-content-left">
                    <span className="btn-primary-title" style={{ fontSize: '1.2rem', textAlign: 'left', whiteSpace: 'normal', lineHeight: '1.3' }}>
                      Q{prob.question_number}: {prob.title || "Programming Task"}
                    </span>
                  </div>
                </div>
                <svg className="btn-arrow-right" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default CS24102Dashboard;
