import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Layout from './components/Layout';
import Overview from './components/Overview';
import CMS from './components/CMS';
import DatabaseExplorer from './components/DatabaseExplorer';
import Settings from './components/Settings';

// Simple Protected Route wrapper
const ProtectedRoute = ({ children }) => {
  const isAuthenticated = localStorage.getItem('bithub_admin_auth') === 'true';
  return isAuthenticated ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Overview />} />
          <Route path="cms" element={<CMS />} />
          <Route path="database" element={<DatabaseExplorer />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
