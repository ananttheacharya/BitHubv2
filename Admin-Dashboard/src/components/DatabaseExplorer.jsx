import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, Database as DbIcon, Search, AlertCircle } from 'lucide-react';

export default function DatabaseExplorer() {
  const [stats, setStats] = useState({ totalQuestions: 0, bySubject: [] });
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [subjectFilter, setSubjectFilter] = useState('all');
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    fetchQuestions();
  }, [subjectFilter, page]);

  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/admin/db/stats');
      setStats({
        totalQuestions: res.data.totalQuestions || 0,
        bySubject: res.data.bySubject || []
      });
    } catch (error) {
      console.error('Failed to fetch DB stats', error);
    }
  };

  const fetchQuestions = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/admin/db/questions?page=${page}&limit=10&subject=${subjectFilter}`);
      setQuestions(res.data || []);
    } catch (error) {
      console.error('Failed to fetch questions', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold mb-1">Database Explorer</h2>
          <p className="text-gray-400">View stats and inspect the questions repository</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg">
          <DbIcon className="w-5 h-5" />
          <span className="text-sm font-medium">DB Connected</span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass p-6 rounded-2xl">
          <div className="text-gray-400 text-sm font-medium mb-2">Total Questions</div>
          <div className="text-4xl font-bold">{stats.totalQuestions}</div>
        </div>
        
        <div className="glass p-6 rounded-2xl md:col-span-2">
          <div className="text-gray-400 text-sm font-medium mb-4">Subject Distribution</div>
          <div className="flex flex-wrap gap-3">
            {stats.bySubject.map((s, i) => (
              <div key={i} className="px-3 py-1.5 bg-black/40 border border-white/10 rounded-lg text-sm">
                <span className="font-semibold text-bithub-accent mr-2">{s.subject}</span>
                <span className="text-gray-300">{s.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Data Grid */}
      <div className="glass rounded-2xl overflow-hidden flex flex-col">
        {/* Toolbar */}
        <div className="p-4 border-b border-white/10 flex justify-between items-center bg-black/20">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 w-4 h-4" />
              <input type="text" placeholder="Search questions..." className="bg-black/40 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-sm text-white focus:outline-none focus:border-bithub-accent w-64" />
            </div>
            
            <select 
              value={subjectFilter} 
              onChange={e => { setSubjectFilter(e.target.value); setPage(1); }}
              className="bg-black/40 border border-white/10 rounded-lg py-2 px-4 text-sm text-white outline-none focus:border-bithub-accent"
            >
              <option value="all">All Subjects</option>
              {stats.bySubject.map((s, i) => (
                <option key={i} value={s.subject}>{s.subject}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-300">
            <thead className="text-xs uppercase bg-black/40 text-gray-400 border-b border-white/10">
              <tr>
                <th className="px-6 py-4">ID</th>
                <th className="px-6 py-4">Subject</th>
                <th className="px-6 py-4">Type</th>
                <th className="px-6 py-4">Difficulty</th>
                <th className="px-6 py-4 w-1/2">Question Preview</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-gray-500">Loading data...</td>
                </tr>
              ) : questions.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-gray-500">No questions found.</td>
                </tr>
              ) : (
                questions.map((q) => (
                  <tr key={q.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs">{q.id.substring(0, 8)}...</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 bg-bithub-accent/20 text-bithub-accent rounded text-xs font-semibold">{q.subject_code}</span></td>
                    <td className="px-6 py-4 truncate max-w-xs">{q.question_type}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${q.difficulty === 'Hard' ? 'bg-red-500/20 text-red-400' : q.difficulty === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                        {q.difficulty}
                      </span>
                    </td>
                    <td className="px-6 py-4 truncate max-w-md">{q.question_text.substring(0, 100)}...</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-4 border-t border-white/10 flex justify-between items-center bg-black/20">
          <span className="text-sm text-gray-400">Page {page}</span>
          <div className="flex gap-2">
            <button 
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              Previous
            </button>
            <button 
              onClick={() => setPage(p => p + 1)}
              disabled={questions.length < 10}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
