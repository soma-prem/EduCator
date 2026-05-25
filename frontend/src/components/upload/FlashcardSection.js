function FlashcardSection({ flashcards, knownMap = null, onMark = null }) {
  if (flashcards.length === 0) {
    return null;
  }

  return (
    <section className="result-section">
      <h3>Flashcards</h3>
      <div className="flashcard-grid">
        {flashcards.map((item, index) => {
          const selection = knownMap ? knownMap[index] : undefined;
          const canMark = typeof onMark === "function";
          return (
            <div key={`fc-wrap-${index}`}>
              <article className="flip-card" key={`fc-${index}`}>
                <div className="flip-card-inner">
                  <div className="flip-card-face flip-card-front">
                    <p className="flashcard-label">Question</p>
                    <div className="flashcard-scroll">
                      <p className="flashcard-text">{item.front}</p>
                    </div>
                  </div>
                  <div className="flip-card-face flip-card-back">
                    <p className="flashcard-label">Answer</p>
                    <div className="flashcard-scroll">
                      <p className="flashcard-text">{item.back}</p>
                    </div>
                  </div>
                </div>
              </article>
              {canMark && (
                <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.55rem", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="ghost-btn"
                    onClick={() => onMark(index, true)}
                    disabled={selection === true}
                  >
                    I knew this
                  </button>
                  <button
                    type="button"
                    className="ghost-btn"
                    onClick={() => onMark(index, false)}
                    disabled={selection === false}
                  >
                    Need review
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default FlashcardSection;
