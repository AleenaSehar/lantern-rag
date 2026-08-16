function App() {
  return (
    <main className="app-shell">
      <header className="app-header">
        <a className="wordmark" href="/" aria-label="groundwork home">
          groundwork
        </a>
        <span className="phase-label">Phase 0</span>
      </header>

      <section className="empty-state" aria-labelledby="page-title">
        <p className="eyebrow">Document Q&amp;A</p>
        <h1 id="page-title">Build answers on evidence.</h1>
        <p>
          The application shell is ready. Document upload, retrieval, and visible source
          citations arrive in the next phases.
        </p>
      </section>
    </main>
  );
}

export default App;

