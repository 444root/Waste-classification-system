'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError, getToken, setToken, User } from '@/lib/api';

interface HistoryItem {
  id: string;
  originalName: string;
  category: string;
  confidence: number;
  accepted: boolean;
  modelVersion: string;
  createdAt: string;
}

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function HistoryPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!getToken()) return router.replace('/login');
    Promise.all([api<User>('/auth/me'), api<HistoryItem[]>('/classifications/history')])
      .then(([account, history]) => {
        setUser(account);
        setItems(history);
      })
      .catch((cause) => {
        if (cause instanceof ApiError && cause.status === 401) return router.replace('/login');
        setError(cause instanceof ApiError ? cause.message : 'Unable to load history');
      });
  }, [router]);

  function logout() {
    setToken(null);
    router.replace('/login');
  }

  return (
    <main className="app-shell records-shell">
      <nav className="topbar">
        <Link href="/classify" className="brand brand-with-mark"><span className="brand-mark">S</span>SORTWISE</Link>
        <div className="account-chip"><Link href="/classify">Classify</Link>{user?.role === 'admin' && <Link href="/admin">Admin</Link>}<span>{user?.name}</span><button onClick={logout}>Log out</button></div>
      </nav>
      <header className="records-header"><p className="eyebrow">Your activity</p><h1>Classification history</h1><p>Review your latest 100 predictions and identify examples worth correcting.</p></header>
      {error && <p className="form-error">{error}</p>}
      {!error && items.length === 0 && <div className="empty-state"><h2>No classifications yet</h2><p>Your results will appear here after your first upload.</p><Link className="primary-button button-link" href="/classify">Classify an item</Link></div>}
      <div className="record-grid">
        {items.map((item) => <article className="record-card" key={item.id}><div><span className={`status-dot ${item.accepted ? 'accepted' : 'uncertain'}`} />{item.accepted ? 'Accepted' : 'Uncertain'}</div><h2>{item.accepted ? label(item.category) : 'Not recognized'}</h2><strong>{Math.round(item.confidence * 100)}%</strong><p>{item.originalName}</p><time>{new Date(item.createdAt).toLocaleString()}</time></article>)}
      </div>
    </main>
  );
}
