'use client';

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, ApiError, getToken, setToken, User } from '@/lib/api';

interface ClassificationResult {
  category: string;
  rawCategory: string;
  confidence: number;
  accepted: boolean;
  secondChoice: string;
  confidenceMargin: number;
  probabilities: Record<string, number>;
  recommendation: string;
  modelVersion: string;
}

const correctionOptions = [
  ['glass', 'Glass'],
  ['metal', 'Metal'],
  ['general_trash', 'General trash'],
  ['organic', 'Organic'],
  ['paper', 'Paper'],
  ['plastic', 'Plastic'],
  ['other', 'Other or unsupported'],
] as const;

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
  const [feedbackMode, setFeedbackMode] = useState<'idle' | 'correcting' | 'saved'>('idle');
  const [correctedCategory, setCorrectedCategory] = useState('');
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    if (result) {
      document.getElementById('classification-result')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  }, [result]);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    if (preview) URL.revokeObjectURL(preview);
    setFile(selected);
    setPreview(selected ? URL.createObjectURL(selected) : '');
    setResult(null);
    setError('');
    setFeedbackMode('idle');
    setCorrectedCategory('');
    setFeedbackError('');
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

  function classifyAnotherItem() {
    setFile(null);
    setPreview('');
    setResult(null);
    setError('');
    setFeedbackMode('idle');
    setCorrectedCategory('');
    setFeedbackError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function submitFeedback(actualCategory: string) {
    if (!file || !result) return;
    setFeedbackLoading(true);
    setFeedbackError('');
    const form = new FormData();
    form.append('file', file);
    form.append('predictedCategory', result.category);
    form.append('correctedCategory', actualCategory);
    form.append('confidence', String(result.confidence));
    try {
      await api('/classifications/feedback', { method: 'POST', body: form });
      setFeedbackMode('saved');
    } catch (cause) {
      setFeedbackError(cause instanceof ApiError ? cause.message : 'Unable to save feedback');
    } finally {
      setFeedbackLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <nav className="topbar">
        <div><span className="brand-mark">S</span><span className="brand">SORTWISE</span></div>
        <div className="account-chip"><Link href="/history">History</Link>{user?.role === 'admin' && <Link href="/admin">Admin</Link>}<span>{user?.name ?? 'Loading...'}</span><button onClick={logout}>Log out</button></div>
      </nav>

      <section className="hero-grid">
        <div className="hero-copy">
          <p className="eyebrow">Image recognition for responsible sorting</p>
          <h1>What are you<br /><em>throwing away?</em></h1>
          <p className="hero-note">Photograph one clear waste item in good light. Center it, move close, and keep other objects outside the frame. Works with iPhone and Android.</p>
          <div className="category-list"><span>Glass</span><span>Metal</span><span>General trash</span><span>Organic</span><span>Paper</span><span>Plastic</span></div>
        </div>

        <form className="upload-panel" onSubmit={submit}>
          <label className={`drop-zone ${preview ? 'has-image' : ''}`}>
            {preview ? <img src={preview} alt="Selected waste item preview" /> : <><span className="upload-icon">+</span><strong>Take or choose a waste photo</strong><small>JPG, PNG, WebP or HEIC, maximum 12 MB</small><span className="camera-guidance">One centered item. Plain background. Good light.</span></>}
            <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif" onChange={chooseFile} />
          </label>
          <button className="primary-button classify-button" disabled={!file || loading}>{loading ? 'Looking closely...' : 'Classify this item'}</button>
          {error && <p className="form-error">{error}</p>}
        </form>
      </section>

      {result && (
        <section id="classification-result" className={`result-card ${result.accepted ? 'accepted' : 'uncertain'}`}>
          <div className="result-toolbar">
            <button type="button" className="secondary-button" onClick={classifyAnotherItem}>Back to upload</button>
          </div>
          <div className="result-heading">
            <div><p className="eyebrow">{result.accepted ? 'Classification result' : 'Unsupported or uncertain item'}</p><h2>{result.accepted ? label(result.category) : 'Item not recognized'}</h2></div>
            <div className="confidence"><strong>{Math.round(result.confidence * 100)}%</strong><span>confidence</span></div>
          </div>
          {!result.accepted && <p className="uncertain-note">The model cannot identify this item reliably. Its possible matches are {label(result.category)} and {label(result.secondChoice)}, but neither should be treated as the answer. Try a supported waste item or take a closer photo against a plain background.</p>}
          <div className="guidance"><span>{result.accepted ? 'Recommended next step' : 'What to do'}</span><p>{result.accepted ? result.recommendation : 'Do not use this prediction for disposal guidance. The item may use a material, such as textile or ceramic, that the current model does not support.'}</p></div>
          <div className="probabilities">
            {probabilities.map(([name, value]) => <div key={name}><span>{label(name)}</span><div><i style={{ width: `${Math.max(value * 100, 1)}%` }} /></div><b>{Math.round(value * 100)}%</b></div>)}
          </div>
          <div className="feedback-card">
            {feedbackMode === 'saved' ? (
              <p className="feedback-success">Feedback saved. This example can now be used for model evaluation and fine-tuning.</p>
            ) : feedbackMode === 'correcting' ? (
              <>
                <p className="feedback-title">What is the actual material?</p>
                <select value={correctedCategory} onChange={(event) => setCorrectedCategory(event.target.value)}>
                  <option value="">Select the correct material</option>
                  {correctionOptions.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
                </select>
                <div className="feedback-actions">
                  <button type="button" className="secondary-button" onClick={() => setFeedbackMode('idle')} disabled={feedbackLoading}>Cancel</button>
                  <button type="button" className="primary-button" onClick={() => submitFeedback(correctedCategory)} disabled={!correctedCategory || feedbackLoading}>{feedbackLoading ? 'Saving...' : 'Save correction'}</button>
                </div>
              </>
            ) : (
              <>
                <p className="feedback-title">Was this classification correct?</p>
                <p className="feedback-note">Submitting feedback securely saves this photo so it can improve future model training.</p>
                <div className="feedback-actions">
                  <button type="button" className="secondary-button" onClick={() => submitFeedback(result.category)} disabled={feedbackLoading}>{feedbackLoading ? 'Saving...' : 'Yes, correct'}</button>
                  <button type="button" className="primary-button" onClick={() => setFeedbackMode('correcting')} disabled={feedbackLoading}>No, correct it</button>
                </div>
              </>
            )}
            {feedbackError && <p className="form-error">{feedbackError}</p>}
          </div>
          <p className="model-note">Baseline model: {result.modelVersion}. This educational prediction does not replace local disposal guidance.</p>
          <div className="result-actions">
            <button type="button" className="primary-button" onClick={classifyAnotherItem}>Classify another item</button>
          </div>
        </section>
      )}
    </main>
  );
}
