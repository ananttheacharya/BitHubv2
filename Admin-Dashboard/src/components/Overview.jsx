import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, Square, Activity, Server, Globe } from 'lucide-react';

export default function Overview() {
  const [status, setStatus] = useState({ frontend: false, ngrok: false, repoPath: '' });
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const res = await axios.get('/api/admin/status');
      setStatus(res.data);
    } catch (error) {
      console.error('Failed to fetch status', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleProcess = async (processName, action) => {
    try {
      setLoading(true);
      await axios.post(`/api/admin/process/${processName}/${action}`);
      setTimeout(fetchStatus, 2000);
    } catch (error) {
      alert(error.response?.data?.error || `Failed to ${action} ${processName}`);
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-3xl font-bold mb-1">Control Center</h2>
          <p className="text-gray-400">Manage BitHuB's local servers and tunneling</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-black/20 rounded-lg border border-white/5">
          <Activity className="w-5 h-5 text-bithub-accent" />
          <span className="text-sm font-medium">System Online</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Frontend Server Card */}
        <div className="glass p-6 rounded-2xl">
          <div className="flex items-center gap-4 mb-6">
            <div className={`p-3 rounded-xl ${status.frontend ? 'bg-green-500/20 text-green-500' : 'bg-gray-500/20 text-gray-400'}`}>
              <Server className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-semibold">Local Frontend</h3>
              <p className="text-sm text-gray-400">BitHuB landing page & study materials</p>
            </div>
          </div>
          
          <div className="flex items-center justify-between mt-8">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${status.frontend ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-sm font-medium text-gray-300">
                {status.frontend ? 'Running (Port 3000)' : 'Offline'}
              </span>
            </div>

            <div className="flex gap-3">
              {status.frontend ? (
                <button 
                  onClick={() => handleProcess('frontend', 'stop')}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/50 rounded-lg font-medium transition-colors"
                >
                  <Square className="w-4 h-4" /> Stop
                </button>
              ) : (
                <button 
                  onClick={() => handleProcess('frontend', 'start')}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-bithub-accent hover:bg-bithub-accent-hover text-white rounded-lg font-medium transition-colors"
                >
                  <Play className="w-4 h-4" /> Start Frontend
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Ngrok Tunnel Card */}
        <div className="glass p-6 rounded-2xl">
          <div className="flex items-center gap-4 mb-6">
            <div className={`p-3 rounded-xl ${status.ngrok ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'}`}>
              <Globe className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-semibold">Ngrok Tunnel</h3>
              <p className="text-sm text-gray-400">Expose frontend to the public web</p>
            </div>
          </div>
          
          <div className="flex items-center justify-between mt-8">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${status.ngrok ? 'bg-blue-400 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-sm font-medium text-gray-300">
                {status.ngrok ? 'Active (unpicked-mignon-unlawyerlike.ngrok-free.dev)' : 'Offline'}
              </span>
            </div>

            <div className="flex gap-3">
              {status.ngrok ? (
                <button 
                  onClick={() => handleProcess('ngrok', 'stop')}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/50 rounded-lg font-medium transition-colors"
                >
                  <Square className="w-4 h-4" /> Stop
                </button>
              ) : (
                <button 
                  onClick={() => handleProcess('ngrok', 'start')}
                  disabled={loading || !status.frontend}
                  title={!status.frontend ? "Start Frontend first" : ""}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play className="w-4 h-4" /> Start Ngrok
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
