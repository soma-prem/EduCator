function HistoryPanel({
  historyItems,
  historyLoading,
  expandedHistoryId,
  onClearHistory,
  onToggleDetails,
  onDeleteItem,
}) {
  return (
    <section className="history-panel">
      <div className="history-header">
        <h3>Study Resource History</h3>
        <button type="button" className="history-clear-btn" onClick={onClearHistory}>
          Clear History
        </button>
      </div>
      {historyLoading && <p>Loading history...</p>}
      {!historyLoading && historyItems.length === 0 && <p>No history found yet.</p>}
      {!historyLoading && historyItems.length > 0 && (
        <ul className="history-list">
          {historyItems.map((item) => (
            <li key={item.id} className="history-item">
              <div className="history-item-head">
                <p>
                  <strong>Source:</strong> {item.sourceType || "source"} | <strong>MCQ Score:</strong>{" "}
                  {item.mcqCorrect || 0}/{item.mcqTotal || 0}
                </p>
                <button
                  type="button"
                  className="history-delete-btn"
                  onClick={() => onDeleteItem(item.id)}
                  aria-label="Delete history item"
                  title="Delete history item"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      d="M9 3h6l1 2h5v2H3V5h5l1-2zm1 6h2v9h-2V9zm4 0h2v9h-2V9zM7 9h2v9H7V9z"
                      fill="currentColor"
                    />
                  </svg>
                </button>
              </div>
              <p className="history-preview">{item.sourcePreview || "(no preview)"}</p>
              <p className="history-time">{item.createdAt}</p>
              <button type="button" className="history-detail-btn" onClick={() => onToggleDetails(item.id)}>
                {expandedHistoryId === item.id ? "Hide Details" : "View Details"}
              </button>
              {expandedHistoryId === item.id && (
                <div className="history-details">
                  {item.summary && (
                    <>
                      <h4>Summary</h4>
                      <pre className="summary-text">{item.summary}</pre>
                    </>
                  )}
                  {Array.isArray(item.mcqs) && item.mcqs.length > 0 && (
                    <>
                      <h4>MCQs</h4>
                      <ol className="history-mcq-list">
                        {item.mcqs.map((mcq, idx) => (
                          <li key={`h-mcq-${item.id}-${idx}`}>
                            <p className="result-question">{mcq.question}</p>
                            <ul className="result-options">
                              {(mcq.options || []).map((opt, optIndex) => (
                                <li key={`h-mcq-${item.id}-${idx}-opt-${optIndex}`}>{opt}</li>
                              ))}
                            </ul>
                            <p className="history-answer">
                              Answer: <strong>{mcq.answer}</strong>
                            </p>
                          </li>
                        ))}
                      </ol>
                    </>
                  )}
                  {Array.isArray(item.flashcards) && item.flashcards.length > 0 && (
                    <>
                      <h4>Flashcards</h4>
                      <div className="history-flashcards">
                        {item.flashcards.map((fc, idx) => (
                          <div className="history-flashcard" key={`h-fc-${item.id}-${idx}`}>
                            <p>
                              <strong>Q:</strong> {fc.front}
                            </p>
                            <p>
                              <strong>A:</strong> {fc.back}
                            </p>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default HistoryPanel;
