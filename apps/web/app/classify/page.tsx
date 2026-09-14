'use client';

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError, getToken, setToken, User } from '@/lib/api';

interface ClassificationResult {
  category: string;
  rawCategory: string;
  confidence: number;
  accepted: boolean;
  probabilities: Record<string, number>;
  recommendation: string;
  modelVersion: string;
}

function label(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function ClassifyPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [result, setResult] = useState<ClassificationResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace('/login');
      return;
    }
    api<User>('/auth/me').then(setUser).catch(() => router.replace('/login'));
  }, [router]);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const probabilities = useMemo(
    () => result ? Object.entries(result.probabilities).sort((a, b) => b[1] - a[1]) : [],
    [result],
  );

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    if (preview) URL.revokeObjectURL(preview);
    setFile(selected);
    setPreview(selected ? URL.createObjectURL(selected) : '');
    setResult(null);
    setError('');
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return setError('Choose an image first');
    setError('');
    setLoading(true);
    const form = new FormData();
    form.append('file', file);
    try {
      setResult(await api<ClassificationResult>('/classifications', { method: 'POST', body: form }));
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) router.replace('/login');
      setError(cause instanceof ApiError ? cause.message : 'Unable to classify this image');
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setToken(null);
    router.replace('/login');
  }

  return (
    <main className="app-shell">
      <nav className="topbar">
        <div><span className="brand-mark">S</span><span className="brand">SORTWISE</span></div>
        <div className="account-chip"><span>{user?.name ?? 'Loading...'}</span><button onClick={logout}>Log out</button></div>
      </nav>

      <section className="hero-grid">
        <div className="hero-copy">
          <p className="eyebrow">Image recognition for responsible sorting</p>
          <h1>What are you<br /><em>throwing away?</em></h1>
          <p className="hero-note">Photograph one clear waste item in good light. We will identify its material and suggest the appropriate stream.</p>
          <div className="category-list"><span>Glass</span><span>Metal</span><span>General trash</span><span>Organic</span><span>Paper</span><span>Plastic</span></div>
        </div>

        <form className="upload-panel" onSubmit={submit}>
          <label className={`drop-zone ${preview ? 'has-image' : ''}`}>
            {preview ? <img src={preview} alt="Selected waste item preview" /> : <><span className="upload-icon">+</span><strong>Choose a waste image</strong><small>JPG, PNG or WebP, maximum 5 MB</small></>}
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseFile} />
          </label>
          <button className="primary-button classify-button" disabled={!file || loading}>{loading ? 'Looking closely...' : 'Classify this item'}</button>
          {error && <p className="form-error">{error}</p>}
        </form>
      </section>

      {result && (
        <section className={`result-card ${result.accepted ? 'accepted' : 'uncertain'}`}>
          <div className="result-heading">
            <div><p className="eyebrow">{result.accepted ? 'Classification result' : 'Uncertain result'}</p><h2>{label(result.category)}</h2></div>
            <div className="confidence"><strong>{Math.round(result.confidence * 100)}%</strong><span>confidence</span></div>
          </div>
          {!result.accepted && <p className="uncertain-note">The confidence is below 70%. Try a closer image with one object and a plain background.</p>}
          <div className="guidance"><span>Recommended next step</span><p>{result.recommendation}</p></div>
          <div className="probabilities">
            {probabilities.map(([name, value]) => <div key={name}><span>{label(name)}</span><div><i style={{ width: `${Math.max(value * 100, 1)}%` }} /></div><b>{Math.round(value * 100)}%</b></div>)}
          </div>
          <p className="model-note">Baseline model: {result.modelVersion}. This educational prediction does not replace local disposal guidance.</p>
        </section>
      )}
    </main>
  );
}

