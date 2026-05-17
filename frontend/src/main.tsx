import React from 'react';
import ReactDOM from 'react-dom/client';
import App from '@/app/App';
import '@/styles/globals.css';

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  override render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100vh', background: '#080c14',
          color: '#e8f4ff', fontFamily: 'monospace', padding: '2rem', gap: '1rem',
        }}>
          <div style={{ color: '#ff4466', fontSize: '1.25rem', fontWeight: 600 }}>
            JARVIS — Render Error
          </div>
          <pre style={{
            background: '#0d1424', border: '1px solid rgba(255,68,102,0.4)',
            padding: '1rem', borderRadius: '6px', maxWidth: '600px',
            whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            color: '#ff4466', fontSize: '0.75rem',
          }}>
            {this.state.error.message}
            {'\n\n'}
            {this.state.error.stack}
          </pre>
          <button
            style={{
              border: '1px solid #00d4ff', color: '#00d4ff', background: 'transparent',
              padding: '0.5rem 1.5rem', borderRadius: '4px', cursor: 'pointer',
              fontFamily: 'monospace',
            }}
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
