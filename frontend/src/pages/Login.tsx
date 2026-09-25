import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { Loader2, AlertCircle, Zap, Factory, Flame, Lightbulb, Cog, Shield } from 'lucide-react';
import { loginFn } from '../api/auth';
import type { LoginPayload } from '../api/auth';
import { useAuthStore } from '../store/authStore';

const loginSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean(),
});
type LoginForm = z.infer<typeof loginSchema>;

const LogoMark: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 32 20" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M10 10C10 6.686 12.686 4 16 4C19.314 4 22 6.686 22 10C22 13.314 19.314 16 16 16" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
    <path d="M22 10C22 6.686 24.686 4 28 4C31.314 4 34 6.686 34 10C34 13.314 31.314 16 28 16C24.686 16 22 13.314 22 10Z" stroke="currentColor" strokeWidth="2.5"/>
    <path d="M16 10C16 13.314 13.314 16 10 16C6.686 16 4 13.314 4 10C4 6.686 6.686 4 10 4" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
  </svg>
);

const sectors = [
  { icon: Flame,     label: 'Oil & Gas' },
  { icon: Zap,       label: 'Power' },
  { icon: Factory,   label: 'Manufacturing' },
  { icon: Cog,       label: 'Engineering' },
  { icon: Lightbulb, label: 'Energy' },
];

const NicBadge: React.FC = () => (
  <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/20 w-fit"
    style={{ background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(4px)' }}>
    <Shield size={14} className="text-white/70" />
    <span className="text-[11px] font-semibold text-white/70 tracking-wide">NIC · Government of India</span>
  </div>
);

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { rememberMe: false, username: '', password: '' },
  });

  const mutation = useMutation({
    mutationFn: loginFn,
    onSuccess: async (data, variables) => {
      const remember = (variables as any).rememberMe;
      await setAuth(data.access_token, remember);
      navigate('/');
    },
  });

  const onSubmit = (data: LoginForm) => {
    mutation.mutate({
      username: data.username,
      password: data.password,
      rememberMe: data.rememberMe,
    } as LoginPayload & { rememberMe: boolean });
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row overflow-hidden">

      {/* ═══ LEFT COLUMN — white form panel ═══ */}
      <div className="flex-1 lg:max-w-[480px] bg-white flex flex-col justify-center px-8 sm:px-12 py-12 relative">
        <div className="tricolor-strip absolute top-0 left-0 right-0" />

        {/* Logo */}
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: 'hsl(155 73% 21% / 0.10)' }}>
            <LogoMark className="w-6 h-5 text-primary" />
          </div>
          <div>
            <p className="font-heading font-bold text-sm text-foreground tracking-tight leading-none">MaterialALX</p>
            <p className="text-[10px] text-muted-foreground font-medium leading-none mt-0.5">Harmonization Platform</p>
          </div>
        </div>

        {/* Heading */}
        <div className="mb-8">
          <h1 className="font-heading font-bold text-foreground leading-tight mb-1"
            style={{ fontSize: 'clamp(1.5rem,3vw,2rem)', letterSpacing: '-0.02em' }}>
            Welcome back
          </h1>
          <p className="text-sm text-muted-foreground">Sign in to your organization account</p>
        </div>

        {/* Error */}
        {mutation.isError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3 text-red-700">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <p className="text-sm font-medium">Authentication failed. Please verify your credentials or check if the backend is running.</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5 uppercase tracking-wider">Username</label>
            <input type="text" {...register('username')} placeholder="Enter your username" className="input-field" />
            {errors.username && <p className="mt-1.5 text-xs text-destructive font-medium">{errors.username.message}</p>}
          </div>

          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5 uppercase tracking-wider">Password</label>
            <input type="password" {...register('password')} placeholder="••••••••" className="input-field" />
            {errors.password && <p className="mt-1.5 text-xs text-destructive font-medium">{errors.password.message}</p>}
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer select-none">
              <input type="checkbox" {...register('rememberMe')} className="w-4 h-4 rounded border-border accent-primary" />
              <span>Remember session</span>
            </label>
            <a href="#" className="text-sm font-semibold hover:underline" style={{ color: 'hsl(var(--primary))' }}>
              Forgot password?
            </a>
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full h-11 flex items-center justify-center gap-2 rounded-lg text-sm font-semibold text-white transition-all duration-150 disabled:opacity-60 disabled:cursor-not-allowed hover:-translate-y-px"
            style={{
              background: mutation.isPending ? 'hsl(155,73%,21%)' : 'linear-gradient(135deg,hsl(155,73%,18%),hsl(155,62%,26%))',
              boxShadow: mutation.isPending ? 'none' : '0 4px 14px hsl(155 73% 21% / 0.35)',
            }}
          >
            {mutation.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Sign In'}
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3 my-6">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-muted-foreground font-medium px-1 select-none">or continue with</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* SSO outlined button */}
        <button
          type="button"
          disabled
          title="Government SSO — configure via .env"
          className="w-full h-11 flex items-center justify-center gap-2.5 rounded-lg text-sm font-semibold border cursor-not-allowed opacity-50 transition-all"
          style={{
            color: 'hsl(var(--primary))',
            borderColor: 'hsl(var(--primary) / 0.4)',
            background: 'hsl(155 73% 21% / 0.04)',
          }}
        >
          <Shield size={16} />
          NIC / Government SSO
        </button>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-8 leading-relaxed">
          National Material Intelligence &amp; Harmonization Platform<br />
          <span className="opacity-60">Powered by AI · Secured by Design</span>
        </p>
        <p className="text-center text-[11px] text-muted-foreground/60 mt-3 font-mono">
          Demo: <span className="text-foreground/50">demo_admin</span> / <span className="text-foreground/50">admin123</span>
        </p>
      </div>

      {/* ═══ RIGHT COLUMN — dark panel with landscape ═══ */}
      <div
        className="hidden lg:flex flex-1 flex-col justify-between relative overflow-hidden"
        style={{ backgroundImage: 'url(/login-panel-bg.jpg)', backgroundSize: 'cover', backgroundPosition: 'center center' }}
      >
        <div className="absolute inset-0" style={{ background: 'linear-gradient(160deg,rgba(13,27,30,0.85) 0%,rgba(15,59,43,0.80) 40%,rgba(15,91,61,0.62) 70%,rgba(13,27,30,0.92) 100%)' }} />
        <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px,white 1px,transparent 0)', backgroundSize: '28px 28px' }} />

        {/* Top */}
        <div className="relative z-10 p-8"><NicBadge /></div>

        {/* Centre */}
        <div className="relative z-10 px-10 pb-6">
          <div className="w-12 h-1 rounded-full mb-6" style={{ background: '#F2A93B' }} />
          <h2 className="font-heading font-bold text-white leading-tight mb-4"
            style={{ fontSize: 'clamp(1.8rem,3vw,2.8rem)', letterSpacing: '-0.02em' }}>
            India's National<br />Material Intelligence<br />Platform
          </h2>
          <p className="text-white/65 text-sm leading-relaxed max-w-xs mb-8">
            Harmonizing material masters across public-sector enterprises with AI-driven
            deduplication, taxonomy governance, and national cataloguing.
          </p>

          {/* Stats */}
          <div className="flex flex-wrap gap-3 mb-8">
            {[{ val: '50+', lbl: 'CPSEs' }, { val: '10M+', lbl: 'Materials' }, { val: '95%', lbl: 'Accuracy' }].map((s) => (
              <div key={s.lbl} className="px-4 py-2 rounded-xl text-center"
                style={{ background: 'rgba(255,255,255,0.10)', border: '1px solid rgba(255,255,255,0.15)' }}>
                <p className="text-white font-heading font-bold text-lg leading-none">{s.val}</p>
                <p className="text-white/55 text-[10px] font-medium mt-0.5">{s.lbl}</p>
              </div>
            ))}
          </div>

          {/* Industry icons */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {sectors.map(({ icon: Icon, label }) => (
              <div key={label} title={label}
                className="flex flex-col items-center gap-1.5 px-3 py-2.5 rounded-xl cursor-default"
                style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)' }}>
                <Icon size={18} className="text-white/75" />
                <span className="text-[9px] text-white/50 font-semibold uppercase tracking-wide">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom tricolor */}
        <div className="relative z-10"><div className="tricolor-strip" /></div>
      </div>

    </div>
  );
};
