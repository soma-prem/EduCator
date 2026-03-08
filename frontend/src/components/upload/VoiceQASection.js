function VoiceQASection({
  question,
  onQuestionChange,
  onAsk,
  answer,
  loading,
  listening,
  onToggleMic,
  audioUrl,
}) {
  return (
    <section className="result-section">
      <div className="summary-header">
        <h3>Voice Question Answering</h3>
        <div className="summary-actions">
          <button type="button" className={`voice-mic-btn ${listening ? "voice-mic-live" : ""}`} onClick={onToggleMic}>
            {listening ? "Stop Mic" : "Mic"}
          </button>
        </div>
      </div>

      <div className="voice-qa-controls">
        <input
          type="text"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="Ask a question about your uploaded content..."
        />
        <button type="button" className="ghost-btn" onClick={onAsk} disabled={loading || !question.trim()}>
          {loading ? "Answering..." : "Ask"}
        </button>
      </div>

      {answer && (
        <div className="summary-text" style={{ marginTop: "0.7rem" }}>
          {answer}
        </div>
      )}

      {audioUrl && (
        <div className="summary-audio">
          <audio controls src={audioUrl} autoPlay />
        </div>
      )}
    </section>
  );
}

export default VoiceQASection;
