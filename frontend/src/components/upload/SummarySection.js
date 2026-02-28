function SummarySection({ summary, speaking, onSpeak, audioLoading, onGenerateAudio, audioUrl }) {
  if (!summary) {
    return null;
  }

  return (
    <section className="result-section">
      <div className="summary-header">
        <h3>Summary</h3>
        <div className="summary-actions">
          <button type="button" className="summary-speak-btn" onClick={onSpeak}>
            {speaking ? "Stop" : "Speak"}
          </button>
          <button type="button" className="summary-audio-btn" onClick={onGenerateAudio} disabled={audioLoading}>
            {audioLoading ? "Generating Audio..." : "Generate Audio"}
          </button>
        </div>
      </div>
      <pre className="summary-text">{summary}</pre>
      {audioUrl && (
        <div className="summary-audio">
          <audio controls src={audioUrl} />
        </div>
      )}
    </section>
  );
}

export default SummarySection;
