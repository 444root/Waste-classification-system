'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { api, ApiError } from '@/lib/api';

interface ForgotPasswordResponse {
  message: string;
  resetUrl?: string;
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [resetUrl, setResetUrl] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setMessage('');
    setResetUrl('');
    setLoading(true);
    try {
      const response = await api<ForgotPasswordResponse>('/auth/forgot-password', {
        method: 'POST',
        auth: false,
        body: { email },
      });
      setMessage(response.message);
      setResetUrl(response.resetUrl ?? '');
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Unable to request a reset link');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <p className="eyebrow">Account recovery</p>
        <h1>Return to<br />better sorting.</h1>
        <p>Enter your account email and we will prepare a secure, time-limited password reset link.</p>
        <div className="material-strip" aria-hidden="true"><span /><span /><span /><span /></div>
      </section>
      <section className="auth-card">
        <Link href="/" className="brand">SORTWISE</Link>
        <p className="eyebrow">Forgot your password?</p>
        <h2>Recover your account</h2>
        <form onSubmit={submit} className="form-stack">
          <label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" /></label>
          {error && <p className="form-error">{error}</p>}
          {message && <p className="form-success">{message}</p>}
          {resetUrl && <Link className="development-link" href={resetUrl}>Open local reset link</Link>}
          <button className="primary-button" disabled={loading}>{loading ? 'Preparing link...' : 'Send reset link'}</button>
        </form>
        <p className="auth-switch"><Link href="/login">Back to sign in</Link></p>
      </section>
    </main>
  );
}
