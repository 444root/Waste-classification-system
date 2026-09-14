'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { PasswordField } from '@/components/password-field';
import { api, ApiError } from '@/lib/api';

export default function ResetPasswordPage() {
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get('token') ?? '');
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!token) {
      setError('This reset link is missing its security token. Request a new link.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const response = await api<{ message: string }>('/auth/reset-password', {
        method: 'POST',
        auth: false,
        body: { token, password },
      });
      setMessage(response.message);
      setPassword('');
      setConfirmPassword('');
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Unable to reset password');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story register-story">
        <p className="eyebrow">Secure account recovery</p>
        <h1>Choose a<br />fresh password.</h1>
        <p>Your reset link works once and expires after 30 minutes. Choose at least eight characters.</p>
        <div className="material-strip" aria-hidden="true"><span /><span /><span /><span /></div>
      </section>
      <section className="auth-card">
        <Link href="/" className="brand">SORTWISE</Link>
        <p className="eyebrow">Reset password</p>
        <h2>Secure your account</h2>
        {message ? (
          <div className="form-stack">
            <p className="form-success">{message}</p>
            <Link className="primary-button button-link" href="/login">Continue to sign in</Link>
          </div>
        ) : (
          <form onSubmit={submit} className="form-stack">
            <PasswordField label="New password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" autoComplete="new-password" />
            <PasswordField label="Confirm password" minLength={8} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Repeat your password" autoComplete="new-password" />
            {error && <p className="form-error">{error}</p>}
            <button className="primary-button" disabled={loading}>{loading ? 'Resetting...' : 'Reset password'}</button>
          </form>
        )}
        <p className="auth-switch"><Link href="/forgot-password">Request another link</Link></p>
      </section>
    </main>
  );
}
