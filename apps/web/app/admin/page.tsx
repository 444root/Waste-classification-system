'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { API_URL, api, ApiError, getToken, setToken, User } from '@/lib/api';

interface AdminOverview {
  stats: { users: number; classifications: number; feedback: number; corrections: number };
  users: Array<{ id: string; name: string; email: string; role: string; classificationCount: number; createdAt: string }>;
  recentClassifications: Array<{ id: string; userName: string; originalName: string; category: string; confidence: number; accepted: boolean; createdAt: string }>;
  recentFeedback: Array<{ id: string; userName: string; predictedCategory: string; correctedCategory: string; confidence: number; originalName: string; createdAt: string }>;
}

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function FeedbackImage({ id, alt }: { id: string; alt: string }) {
  const [source, setSource] = useState('');

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const controller = new AbortController();
    let objectUrl = '';

    fetch(`${API_URL}/admin/feedback/${id}/image`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error('Unable to load feedback image');
        return response.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setSource(objectUrl);
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setSource('');
      });

    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  return source ? <img src={source} alt={alt} /> : <div className="feedback-image-placeholder">Image</div>;
}

export default function AdminPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!getToken()) return router.replace('/login');
    api<User>('/auth/me').then((account) => {
      if (account.role !== 'admin') return router.replace('/classify');
      setUser(account);
      return api<AdminOverview>('/admin/overview').then(setOverview);
    }).catch((cause) => {
      if (cause instanceof ApiError && [401, 403].includes(cause.status)) return router.replace('/classify');
      setError(cause instanceof ApiError ? cause.message : 'Unable to load admin dashboard');
    });
  }, [router]);

  function logout() {
    setToken(null);
    router.replace('/login');
  }

  return (
    <main className="app-shell records-shell">
      <nav className="topbar"><Link href="/classify" className="brand brand-with-mark"><span className="brand-mark">S</span>SORTWISE ADMIN</Link><div className="account-chip"><Link href="/classify">Classify</Link><Link href="/history">History</Link><span>{user?.name}</span><button onClick={logout}>Log out</button></div></nav>
      <header className="records-header"><p className="eyebrow">Administration</p><h1>Model evidence center</h1><p>Monitor adoption, classification behavior, and corrected examples for the next training cycle.</p></header>
      {error && <p className="form-error">{error}</p>}
      {overview && <>
        <section className="stat-grid"><article><span>Users</span><strong>{overview.stats.users}</strong></article><article><span>Classifications</span><strong>{overview.stats.classifications}</strong></article><article><span>Feedback items</span><strong>{overview.stats.feedback}</strong></article><article><span>Corrections</span><strong>{overview.stats.corrections}</strong></article></section>
        <section className="admin-section"><div className="section-heading"><div><p className="eyebrow">User management</p><h2>Registered users</h2></div></div><div className="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Classifications</th><th>Joined</th></tr></thead><tbody>{overview.users.map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.email}</td><td><span className="role-badge">{item.role}</span></td><td>{item.classificationCount}</td><td>{new Date(item.createdAt).toLocaleDateString()}</td></tr>)}</tbody></table></div></section>
        <section className="admin-section"><div className="section-heading"><div><p className="eyebrow">Latest activity</p><h2>Recent classifications</h2></div></div><div className="table-wrap"><table><thead><tr><th>User</th><th>Prediction</th><th>Confidence</th><th>Status</th><th>Time</th></tr></thead><tbody>{overview.recentClassifications.map((item) => <tr key={item.id}><td>{item.userName}</td><td>{label(item.category)}</td><td>{Math.round(item.confidence * 100)}%</td><td>{item.accepted ? 'Accepted' : 'Uncertain'}</td><td>{new Date(item.createdAt).toLocaleString()}</td></tr>)}</tbody></table></div></section>
        <section className="admin-section"><div className="section-heading"><div><p className="eyebrow">Training evidence</p><h2>Recent feedback</h2></div></div>{overview.recentFeedback.length === 0 ? <p className="empty-row">No feedback has been submitted yet.</p> : <div className="feedback-grid">{overview.recentFeedback.map((item) => <article key={item.id}><FeedbackImage id={item.id} alt={item.originalName} /><div><span>{item.userName}</span><strong>{label(item.predictedCategory)} to {label(item.correctedCategory)}</strong><small>{Math.round(item.confidence * 100)}% confidence</small></div></article>)}</div>}</section>
      </>}
    </main>
  );
}
