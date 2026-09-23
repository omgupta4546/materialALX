import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { Loader2, AlertCircle, ShieldCheck } from 'lucide-react';
import { loginFn } from '../api/auth';
import type { LoginPayload } from '../api/auth';
import { useAuthStore } from '../store/authStore';

const loginSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  password: z.string().min(1, "Password is required"),
  rememberMe: z.boolean(),
});

type LoginForm = z.infer<typeof loginSchema>;



export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      rememberMe: false,
      username: '',
      password: ''
    }
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
      rememberMe: data.rememberMe
    } as LoginPayload & { rememberMe: boolean });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden">
      {/* Abstract Background Design */}
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-secondary/30 rounded-full blur-3xl" />

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
              <ShieldCheck className="w-8 h-8 text-primary" />
            </div>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">National Material Hub</h1>
          <p className="text-muted-foreground mt-2">Sign in to your organization</p>
        </div>

        <div className="glass rounded-xl shadow-xl p-8">
          {mutation.isError && (
            <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg flex items-start space-x-3 text-destructive">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="text-sm font-medium">
                Authentication failed. Please verify your credentials or check if the backend is running.
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">


            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Username</label>
              <input
                type="text"
                {...register("username")}
                placeholder="Enter username"
                className="w-full p-2.5 rounded-md border border-border bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all text-foreground"
              />
              {errors.username && <p className="mt-1 text-sm text-destructive">{errors.username.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Password</label>
              <input
                type="password"
                {...register("password")}
                placeholder="••••••••"
                className="w-full p-2.5 rounded-md border border-border bg-background focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none transition-all text-foreground"
              />
              {errors.password && <p className="mt-1 text-sm text-destructive">{errors.password.message}</p>}
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center space-x-2 text-sm text-muted-foreground cursor-pointer">
                <input
                  type="checkbox"
                  {...register("rememberMe")}
                  className="rounded border-border text-primary focus:ring-primary"
                />
                <span>Remember session</span>
              </label>
              <a href="#" className="text-sm text-primary hover:underline">Forgot password?</a>
            </div>

            <button
              type="submit"
              disabled={mutation.isPending}
              className="w-full py-2.5 px-4 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-all disabled:opacity-70 disabled:cursor-not-allowed flex justify-center items-center h-11"
            >
              {mutation.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                "Sign In"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
