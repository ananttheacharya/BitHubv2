import React, { useState } from 'react';
import axios from 'axios';
import { UploadCloud, File, AlertCircle } from 'lucide-react';

export default function CMS() {
  const [file, setFile] = useState(null);
  const [semester, setSemester] = useState('Sem1');
  const [subject, setSubject] = useState('');
  const [type, setType] = useState('notes');
  const [module, setModule] = useState('1');
  
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !subject) {
      setMessage({ type: 'error', text: 'Please fill in all required fields and select a file.' });
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('semester', semester);
    formData.append('subject', subject);
    formData.append('type', type);
    if (type === 'notes') {
      formData.append('module', module);
    }

    setUploading(true);
    setMessage({ type: '', text: '' });

    try {
      const res = await axios.post('/api/admin/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMessage({ type: 'success', text: `File successfully uploaded to: ${res.data.file}` });
      setFile(null); // reset
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.error || 'Upload failed' });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-1">Content Manager</h2>
        <p className="text-gray-400">Directly upload study materials to local repository</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Form Settings */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass p-6 rounded-2xl space-y-4">
            <h3 className="font-semibold text-lg border-b border-white/10 pb-2 mb-4">Target Location</h3>
            
            <div>
              <label className="block text-sm text-gray-400 mb-1">Semester</label>
              <select value={semester} onChange={e => setSemester(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-white outline-none focus:border-bithub-accent">
                <option value="Sem1">Semester 1</option>
                <option value="Sem2">Semester 2</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Subject Code</label>
              <input type="text" placeholder="e.g. CS24101" value={subject} onChange={e => setSubject(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-white outline-none focus:border-bithub-accent uppercase" />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Material Type</label>
              <select value={type} onChange={e => setType(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-white outline-none focus:border-bithub-accent">
                <option value="notes">Module Notes</option>
                <option value="pyq">Question Paper (QPA)</option>
                <option value="reference">Reference Book</option>
              </select>
            </div>

            {type === 'notes' && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Module Number</label>
                <select value={module} onChange={e => setModule(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-lg p-2 text-white outline-none focus:border-bithub-accent">
                  {[1,2,3,4,5].map(m => <option key={m} value={m}>Module {m}</option>)}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Upload Zone */}
        <div className="lg:col-span-2">
          {message.text && (
            <div className={`p-4 rounded-lg mb-6 flex items-start gap-3 border ${message.type === 'success' ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <p className="text-sm font-medium">{message.text}</p>
            </div>
          )}

          <div 
            className={`border-2 border-dashed rounded-2xl p-12 text-center transition-colors ${file ? 'border-bithub-accent bg-bithub-accent/5' : 'border-white/20 bg-black/20 hover:border-white/40 hover:bg-black/40'}`}
            onDragOver={e => e.preventDefault()}
            onDrop={handleDrop}
          >
            <input type="file" id="fileUpload" className="hidden" onChange={handleFileChange} accept=".pdf,.doc,.docx" />
            
            {file ? (
              <div className="flex flex-col items-center">
                <File className="w-16 h-16 text-bithub-accent mb-4" />
                <p className="text-lg font-semibold">{file.name}</p>
                <p className="text-sm text-gray-400 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <div className="mt-6 flex gap-3">
                  <button onClick={() => setFile(null)} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
                    Remove
                  </button>
                  <button onClick={handleUpload} disabled={uploading} className="px-6 py-2 bg-bithub-accent hover:bg-bithub-accent-hover text-white rounded-lg font-medium transition-colors disabled:opacity-50">
                    {uploading ? 'Uploading...' : 'Confirm Upload'}
                  </button>
                </div>
              </div>
            ) : (
              <label htmlFor="fileUpload" className="cursor-pointer flex flex-col items-center">
                <div className="w-20 h-20 bg-black/40 rounded-full flex items-center justify-center mb-4">
                  <UploadCloud className="w-10 h-10 text-gray-400" />
                </div>
                <p className="text-xl font-semibold mb-2">Drag and drop file here</p>
                <p className="text-gray-400 mb-6">or click to browse from your computer</p>
                <span className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg font-medium transition-colors">
                  Select File
                </span>
              </label>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
