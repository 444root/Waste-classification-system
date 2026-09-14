'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError, AuthResponse, setToken } from '@/lib/api';
import { PasswordField } from '@/components/password-field';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const session = await api<AuthResponse>('/auth/login', {
        method: 'POST',
        auth: false,
        body: { email, password },
      });
      setToken(session.accessToken);
      router.replace('/classify');
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Unable to sign in');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <p className="eyebrow">Kigali waste, sorted with clarity</p>
        <h1>One photo.<br />One better decision.</h1>
        <p>Sortwise helps people identify everyday waste and understand the next responsible step.</p>
        <div className="material-strip" aria-hidden="true"><span /><span /><span /><span /></div>
      </section>
      <section className="auth-card">
        <Link href="/" className="brand">SORTWISE</Link>
        <p className="eyebrow">Welcome back</p>
        <h2>Sign in to classify</h2>
        <form onSubmit={submit} className="form-stack">
          <label>Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label>
          <PasswordField label="Password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" autoComplete="current-password" />
          <Link href="/forgot-password" className="form-assist">Forgot password?</Link>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>
        </form>
        <p className="auth-switch">New here? <Link href="/register">Create an account</Link></p>
      </section>
    </main>
  );
}
