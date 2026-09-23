import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Package, CheckSquare, BarChart, LogOut, UploadCloud, Scale, Database, FolderTree, ShieldCheck, Settings } from 'lucide-react';
import { cn } from '../components/common/MetricCard';
import { useAuthStore } from '../store/authStore';

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

  return (
    <div className="w-64 border-r bg-card flex flex-col justify-between h-full">
      <div>
        <div className="p-6 font-bold text-lg border-b border-border text-primary flex items-center space-x-2">
          <Package className="text-primary" />
          <span>Harmonization</span>
        </div>
        <nav className="p-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center space-x-3 px-3 py-2 rounded-md transition-colors",
                location.pathname === item.path 
                  ? "bg-primary text-primary-foreground" 
                  : "hover:bg-accent hover:text-accent-foreground text-muted-foreground"
              )}
            >
              <item.icon size={20} />
              <span>{item.name}</span>
            </Link>
          ))}

          {canAccessGovernance && (
            <>
              {/* Governance divider */}
              <div className="pt-3 pb-1">
                <p className="px-3 text-xs font-semibold text-muted-foreground/50 uppercase tracking-wider">Governance</p>
              </div>

              {governanceItems.map((item) => (
                // Only show admin items if the user is an admin
                (item.adminOnly && !isAdmin) ? null : (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={cn(
                      "flex items-center space-x-3 px-3 py-2 rounded-md transition-colors",
                      location.pathname === item.path
                        ? "bg-primary text-primary-foreground"
                        : item.adminOnly
                          ? "hover:bg-violet-900/30 hover:text-violet-300 text-violet-400/70"
                          : "hover:bg-accent hover:text-accent-foreground text-muted-foreground"
                    )}
                  >
                    <item.icon size={20} />
                    <span>{item.name}</span>
                    {item.adminOnly && <span className="ml-auto text-xs opacity-50">🔒</span>}
                  </Link>
                )
              ))}
            </>
          )}
        </nav>
      </div>
      <div className="p-4 border-t border-border">
        <button 
          onClick={handleLogout}
          className="flex items-center space-x-3 px-3 py-2 w-full text-left text-muted-foreground hover:bg-destructive hover:text-destructive-foreground rounded-md transition-colors"
        >
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
};
