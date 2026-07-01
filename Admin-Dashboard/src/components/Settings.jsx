import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Save, Folder } from 'lucide-react';

export default function Settings() {
  const [repoPath, setRepoPath] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await axios.get('/api/admin/config');
        setRepoPath(res.data.repoPath);
      } catch (error) {
        console.error('Failed to load config', error);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage({ type: '', text: '' });
    try {
      const res = await axios.post('/api/admin/config', { repoPath });
      setRepoPath(res.data.config.repoPath);
      setMessage({ type: 'success', text: 'Repository path updated successfully.' });
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.error || 'Failed to update repository path.' 
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-gray-400">Loading settings...</div>;

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-1">Settings</h2>
        <p className="text-gray-400">Configure your local Admin Dashboard</p>
      </div>

      <div className="glass p-8 rounded-2xl">
        <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
          <Folder className="w-5 h-5 text-bithub-accent" /> Local Helper Configuration
        </h3>
        
        <p className="text-sm text-gray-400 mb-6">
          Set the absolute path to your local cloned BitHuB repository. This path is used by the Control Center to start Vite and Ngrok, and by the CMS to save uploaded files into the "Study Material" folder.
        </p>

        {message.text && (
          <div className={`p-4 rounded-lg mb-6 text-sm border ${
            message.type === 'success' 
              ? 'bg-green-500/10 border-green-500/50 text-green-500' 
              : 'bg-red-500/10 border-red-500/50 text-red-500'
          }`}>
            {message.text}
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">BitHuB Repository Path</label>
            <input 
              type="text" 
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              className="w-full bg-black/30 border border-white/10 rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-bithub-accent transition-colors font-mono text-sm"
              placeholder="e.g. C:\Users\name\Downloads\BITHUBV2"
              required
            />
          </div>

          <button 
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 bg-bithub-accent hover:bg-bithub-accent-hover text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </form>
      </div>
    </div>
  );
}
