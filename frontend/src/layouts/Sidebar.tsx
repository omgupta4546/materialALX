import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Package, CheckSquare, BarChart, LogOut, UploadCloud, Scale, Database, FolderTree, ShieldCheck, Settings } from 'lucide-react';
import { cn } from '../components/common/MetricCard';
import { useAuthStore } from '../store/authStore';

// Interlocking-loop (infinity/link) SVG logo mark
const LogoMark: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 32 20" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path
      d="M10 10C10 6.686 12.686 4 16 4C19.314 4 22 6.686 22 10C22 13.314 19.314 16 16 16"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
    />
    <path
      d="M22 10C22 6.686 24.686 4 28 4C31.314 4 34 6.686 34 10C34 13.314 31.314 16 28 16C24.686 16 22 13.314 22 10Z"
      stroke="currentColor" strokeWidth="2.5"
    />
    <path
      d="M16 10C16 13.314 13.314 16 10 16C6.686 16 4 13.314 4 10C4 6.686 6.686 4 10 4"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
    />
  </svg>
);

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuthStore();
  const isAdmin = user?.role === 'ADMIN';
  const isSteward = user?.role === 'DATA_STEWARD';
  const canAccessGovernance = isAdmin || isSteward;

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Materials', path: '/materials', icon: Package },
    { name: 'Matches', path: '/matches', icon: Scale },
    { name: 'National Codes', path: '/national-materials', icon: Database },
    { name: 'Upload', path: '/upload', icon: UploadCloud },
    { name: 'Approvals', path: '/approvals', icon: CheckSquare },
    { name: 'Analytics', path: '/analytics', icon: BarChart },
  ];

  const governanceItems = [
    { name: 'Taxonomy', path: '/taxonomy', icon: FolderTree, adminOnly: false },
    { name: 'Rules', path: '/rules', icon: ShieldCheck, adminOnly: false },
    { name: 'Admin', path: '/admin', icon: Settings, adminOnly: true },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname === path;

  return (
    <div className="w-64 bg-white border-r border-border flex flex-col h-full" style={{ boxShadow: '1px 0 8px rgba(15,91,61,0.05)' }}>
      {/* Logo / Brand */}
      <div className="px-5 py-5 border-b border-border flex items-center gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-primary/10 shrink-0">
          <LogoMark className="w-6 h-5 text-primary" />
        </div>
        <div className="leading-tight">
          <span className="font-heading font-bold text-sm text-foreground tracking-tight">MaterialALX</span>
          <p className="text-[10px] text-muted-foreground font-medium leading-none mt-0.5">Harmonization Platform</p>
        </div>
      </div>

      {/* Nav */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={cn(
              'nav-link',
              isActive(item.path) && 'active'
            )}
          >
            <item.icon size={18} strokeWidth={isActive(item.path) ? 2.5 : 2} />
            <span>{item.name}</span>
          </Link>
        ))}

        {canAccessGovernance && (
          <>
            <div className="pt-4 pb-1">
              <p className="px-3 text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
                Governance
              </p>
            </div>
            {governanceItems.map((item) =>
              item.adminOnly && !isAdmin ? null : (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'nav-link',
                    isActive(item.path) && 'active',
                    item.adminOnly && !isActive(item.path) && 'text-amber-600/70 hover:text-amber-700 hover:bg-amber-50'
                  )}
                >
                  <item.icon size={18} strokeWidth={isActive(item.path) ? 2.5 : 2} />
                  <span>{item.name}</span>
                  {item.adminOnly && (
                    <span className="ml-auto badge badge-warning text-[9px] px-1.5 py-0 font-bold">ADMIN</span>
                  )}
                </Link>
              )
            )}
          </>
        )}
      </div>

      {/* User + Logout */}
      <div className="px-3 py-4 border-t border-border space-y-1">
        {user && (
          <Link to="/profile" className="flex items-center gap-3 px-3 py-2 mb-1 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-[#0F5B3D] bg-gradient-to-br from-purple-200 to-green-200 shadow-sm shrink-0 border border-white/50">
              {(user.name || 'U').slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-foreground truncate">{user.name}</p>
              <p className="text-[10px] text-muted-foreground truncate capitalize">{(user.role || '').toLowerCase().replace('_', ' ')}</p>
            </div>
          </Link>
        )}
        <button
          onClick={handleLogout}
          className="nav-link w-full text-left text-destructive/80 hover:bg-destructive/8 hover:text-destructive"
        >
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </div>

      {/* Tricolor strip at very bottom */}
      <div className="tricolor-strip" />
    </div>
  );
};

