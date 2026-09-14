'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError, AuthResponse, setToken } from '@/lib/api';
import { PasswordField } from '@/components/password-field';

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const session = await api<AuthResponse>('/auth/register', {
        method: 'POST',
        auth: false,
        body: { name, email, password },
      });
      setToken(session.accessToken);
      router.replace('/classify');
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Unable to create account');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story register-story">
        <p className="eyebrow">A practical college project</p>
        <h1>Train awareness.<br />Reduce mistakes.</h1>
        <p>Start with one clear object per image. The system reports uncertainty instead of pretending every answer is certain.</p>
        <div className="material-strip" aria-hidden="true"><span /><span /><span /><span /></div>
      </section>
      <section className="auth-card">
        <Link href="/" className="brand">SORTWISE</Link>
        <p className="eyebrow">Create your account</p>
        <h2>Start classifying</h2>
        <form onSubmit={submit} className="form-stack">
          <label>Full name<input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" /></label>
          <label>Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label>
          <PasswordField label="Password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" autoComplete="new-password" />
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button" disabled={loading}>{loading ? 'Creating account...' : 'Create account'}</button>
        </form>
        <p className="auth-switch">Already registered? <Link href="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
