function KnowledgeGapSection({ result, loading, onAnalyze }) {
  const weakTopics = Array.isArray(result?.weakTopics) ? result.weakTopics : [];
  const recommendedStudy = Array.isArray(result?.recommendedStudy) ? result.recommendedStudy : [];

  return (
    <section className="result-section">
      <div className="summary-header">
        <h3>Knowledge Gap Detector</h3>
        <div className="summary-actions">
          <button type="button" className="ghost-btn" onClick={onAnalyze} disabled={loading}>
            {loading ? "Analyzing..." : "Analyze Knowledge Gaps"}
          </button>
        </div>
      </div>

      {weakTopics.length === 0 && !loading && (
        <p className="topic-empty-text">No weak topics detected yet. Complete and analyze your quiz attempts.</p>
      )}

      {weakTopics.length > 0 && (
        <>
          <h4>Your Weak Areas</h4>
          <ul className="result-options">
            {weakTopics.map((item) => (
              <li key={item.topic}>
                {item.topic} (accuracy {(Number(item.accuracy || 0) * 100).toFixed(0)}%)
              </li>
            ))}
          </ul>

          <h4>Recommended Study</h4>
          <div className="history-flashcards">
            {recommendedStudy.map((topicBlock) => (
              <article key={topicBlock.topic} className="history-flashcard">
                <p>
                  <strong>{topicBlock.topic}</strong>
                </p>
                <p>
                  Flashcards: {Array.isArray(topicBlock.flashcards) ? topicBlock.flashcards.length : 0} | Revision MCQs:{" "}
                  {Array.isArray(topicBlock.mcqs) ? topicBlock.mcqs.length : 0}
                </p>
                {topicBlock.summary && <p>{topicBlock.summary}</p>}
                {topicBlock.audioBase64 && (
                  <audio controls src={`data:audio/mpeg;base64,${topicBlock.audioBase64}`} style={{ width: "100%" }} />
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export default KnowledgeGapSection;
