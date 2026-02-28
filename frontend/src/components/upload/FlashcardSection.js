function FlashcardSection({ flashcards }) {
  if (flashcards.length === 0) {
    return null;
  }

  return (
    <section className="result-section">
      <h3>Flashcards</h3>
      <div className="flashcard-grid">
        {flashcards.map((item, index) => (
          <article className="flip-card" key={`fc-${index}`}>
            <div className="flip-card-inner">
              <div className="flip-card-face flip-card-front">
                <p className="flashcard-label">Question</p>
                <p className="flashcard-text">{item.front}</p>
              </div>
              <div className="flip-card-face flip-card-back">
                <p className="flashcard-label">Answer</p>
                <p className="flashcard-text">{item.back}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default FlashcardSection;
