import React from 'react';
import { Bell, Search } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export const Topbar: React.FC = () => {
  const { user } = useAuthStore();
  const initials = user?.name
    ? user.name.slice(0, 2).toUpperCase()
    : 'U';

  return (
    <div className="shrink-0">
      <header className="h-14 bg-white border-b border-border flex items-center justify-between px-6" style={{ boxShadow: '0 1px 4px rgba(15,91,61,0.06)' }}>
        {/* Pill Search */}
        <div className="search-pill w-80">
          <Search size={15} className="text-muted-foreground shrink-0" />
          <input
            type="text"
            placeholder="Search materials globally..."
            className="flex-1 bg-transparent border-none outline-none text-sm text-foreground placeholder:text-muted-foreground"
          />
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-3">
          {/* Notification bell */}
          <button
            className="relative p-2 rounded-full text-muted-foreground hover:text-primary hover:bg-primary/8 transition-colors duration-150"
            aria-label="Notifications"
          >
            <Bell size={18} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-accent border-2 border-white animate-pulse-green" />
          </button>

          {/* Divider */}
          <div className="h-6 w-px bg-border" />

          {/* Avatar + username */}
          <div className="flex items-center gap-2.5 cursor-pointer group">
            <div className="avatar-badge">
              {initials}
            </div>
            <div className="hidden sm:block leading-tight">
              <p className="text-xs font-semibold text-foreground leading-none">
                {user?.name || 'User'}
              </p>
              <p className="text-[10px] text-muted-foreground capitalize leading-none mt-0.5">
                {(user?.role || '').toLowerCase().replace('_', ' ')}
              </p>
            </div>
          </div>
        </div>
      </header>
      {/* Tricolor accent strip */}
      <div className="tricolor-strip" />
    </div>
  );
};

