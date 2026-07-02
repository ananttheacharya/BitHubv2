import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import './LabDashboard.css'; // Reuse existing styles
import './OnlineJudge.css';

const OnlineJudge = ({ problem, theme, onBack }) => {
  const [code, setCode] = useState(`#include <stdio.h>\n\n${problem.returnType} ${problem.functionName}() {\n    // Write your code here\n}\n`);
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("idle"); // idle, running, success, error

  const handleEditorChange = (value) => {
    setCode(value);
  };

  const runCode = async () => {
    setLoading(true);
    setStatus("running");
    setOutput("Compiling and running...");

    // For evaluationType: stdout or return_value
    // We send code + first test case input if available
    let testInput = "";
    if (problem.testCases && problem.testCases.length > 0) {
      testInput = (problem.testCases[0].input || []).join(" ");
    }

    try {
      // In production, we'd send multiple requests or a batch to evaluate against all test cases.
      // For MVP, we'll just run it once and output the result.
      const res = await fetch('/api/practice/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: code,
          language: 'c',
          stdin: testInput
        })
      });
      
      const data = await res.json();
      setLoading(false);
      
      if (data.success) {
        setStatus("success");
        setOutput(data.runOutput || "Execution finished with no output.");
      } else {
        setStatus("error");
        setOutput(data.compileError || data.runError || "Unknown error occurred.");
      }
    } catch (err) {
      setLoading(false);
      setStatus("error");
      setOutput(`Error connecting to compiler: ${err.message}`);
    }
  };

  const getStatusColor = () => {
    if (status === "success") return "#4ade80"; // green
    if (status === "error") return "#f87171"; // red
    if (status === "running") return "#60a5fa"; // blue
    return "var(--dash-text-color)";
  };

  return (
    <div className="oj-container" style={{ width: '100%', maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1.5rem', gap: '1rem' }}>
        <button className="back-subjects-btn" onClick={onBack} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'none', border: 'none', color: 'var(--dash-text-color)', cursor: 'pointer', fontFamily: 'var(--font-body)', fontSize: '1rem', fontWeight: '500'}}>
          <svg className="btn-arrow-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{width: 20, height: 20}}>
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          <span>Back</span>
        </button>
        <h2 style={{ fontFamily: 'var(--font-display)', color: 'var(--dash-text-color)', margin: 0 }}>
          Q{problem.question_number}: {problem.title || "Programming Task"}
        </h2>
      </div>

      <div className="oj-layout">
        {/* Left Side: Problem Description */}
        <div className="oj-panel problem-panel">
          <h3 style={{ marginTop: 0, borderBottom: '1px solid var(--glass-border)', paddingBottom: '0.5rem', color: 'var(--dash-text-color)' }}>Problem Statement</h3>
          <p style={{ color: 'var(--dash-text-color)', lineHeight: '1.6', fontSize: '1.1rem' }}>
            {problem.question_text}
          </p>
          
          {problem.testCases && problem.testCases.length > 0 && (
            <div className="oj-test-cases" style={{ marginTop: '2rem' }}>
              <h4 style={{ color: 'var(--dash-text-color)' }}>Sample Test Case</h4>
              <div className="oj-code-block" style={{ background: 'var(--glass-bg)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--glass-border)', color: 'var(--dash-text-color)', fontFamily: 'monospace' }}>
                <div><strong>Input:</strong> {JSON.stringify(problem.testCases[0].input)}</div>
                {problem.evaluationType === "stdout" ? (
                  <div><strong>Expected Output:</strong> {problem.testCases[0].expected_stdout}</div>
                ) : (
                  <div><strong>Expected Return:</strong> {JSON.stringify(problem.testCases[0].expected_return)}</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Editor & Output */}
        <div className="oj-panel editor-panel">
          <div className="oj-editor-header" style={{ padding: '0.5rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--glass-border)', background: 'var(--glass-bg)' }}>
            <span style={{ color: 'var(--dash-text-color)', fontWeight: 'bold' }}>C Compiler (gcc)</span>
            <button 
              className="subject-selection-btn" 
              style={{ padding: '0.5rem 1.5rem', minHeight: 'auto', borderRadius: '6px' }}
              onClick={runCode}
              disabled={loading}
            >
              {loading ? "Running..." : "Run Code"}
            </button>
          </div>
          
          <div className="editor-container">
            <Editor
              height="100%"
              defaultLanguage="c"
              theme={theme === 'dark' ? 'vs-dark' : 'light'}
              value={code}
              onChange={handleEditorChange}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: "'Fira Code', monospace",
                lineHeight: 24,
                padding: { top: 16 },
                scrollBeyondLastLine: false,
                smoothScrolling: true,
                cursorBlinking: "smooth",
                cursorSmoothCaretAnimation: true,
                formatOnPaste: true,
              }}
            />
          </div>

          <div className="output-panel">
            <div style={{ padding: '0.5rem 1rem', borderBottom: '1px solid #333', display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#ccc', background: '#252526' }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{width: 16, height: 16}}>
                <polyline points="4 17 10 11 4 5"></polyline>
                <line x1="12" y1="19" x2="20" y2="19"></line>
              </svg>
              <strong>Console</strong>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: getStatusColor(), marginLeft: 'auto' }}></div>
            </div>
            <div style={{ padding: '1rem', flex: 1, overflowY: 'auto', fontFamily: 'monospace', color: '#e5e5e5', whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>
              {output || "Output will appear here..."}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnlineJudge;
