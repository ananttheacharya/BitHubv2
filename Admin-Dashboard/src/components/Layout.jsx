import React from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileUp, Database, LogOut, Settings } from 'lucide-react';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('bithub_admin_auth');
    navigate('/login');
  };

  const navItems = [
    { path: '/', label: 'Overview', icon: <LayoutDashboard className="w-5 h-5" /> },
    { path: '/cms', label: 'Content Manager', icon: <FileUp className="w-5 h-5" /> },
    { path: '/database', label: 'Database Explorer', icon: <Database className="w-5 h-5" /> },
    { path: '/settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-bithub-dark">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/10 bg-bithub-card flex flex-col">
        <div className="p-6 border-b border-white/10">
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
            BitHuB Admin
          </h1>
          <p className="text-xs text-gray-400 mt-1">Control Center</p>
        </div>

        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive 
                    ? 'bg-bithub-accent/10 text-bithub-accent' 
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                }`}
              >
                {item.icon}
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/10">
          <button 
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 w-full text-left rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto bg-bithub-dark p-8">
        <Outlet />
      </main>
    </div>
  );
}
