function McqSection({
  mcqs,
  mcqVerdicts,
  verifyingAnswers,
  onAnswer,
  isCorrectOption,
  allAnswered,
  correctCount,
  answeredCount,
  totalMcqCount,
}) {
  if (mcqs.length === 0) {
    return null;
  }

  return (
    <section className="result-section">
      <h3>MCQs</h3>
      <ol>
        {mcqs.map((item, index) => (
          <li key={`mcq-${index}`}>
            <p className="result-question">{item.question}</p>
            <ul className="result-options">
              {(item.options || []).map((option, optionIndex) => {
                const verdict = mcqVerdicts[index];
                const selectedOption = verdict?.selectedAnswer;
                const isSelected = selectedOption === option;
                const correctIndex =
                  Number.isInteger(verdict?.correctIndex) && verdict.correctIndex >= 0 ? verdict.correctIndex : null;
                const correctAnswer = verdict?.correctAnswer || item.answer;
                const isCorrect =
                  correctIndex !== null ? optionIndex === correctIndex : isCorrectOption(option, correctAnswer);
                const showResult = Boolean(verdict);

                let optionClass = "mcq-option-btn";
                if (showResult && isCorrect) {
                  optionClass += " mcq-option-correct";
                } else if (showResult && isSelected && !isCorrect) {
                  optionClass += " mcq-option-wrong";
                }
                if (verifyingAnswers[index] && isSelected) {
                  optionClass += " mcq-option-pending";
                }

                return (
                  <li key={`mcq-${index}-opt-${optionIndex}`}>
                    <button
                      type="button"
                      className={optionClass}
                      onClick={() => onAnswer(index, option)}
                      disabled={Boolean(verdict) || Boolean(verifyingAnswers[index])}
                    >
                      {option}
                    </button>
                  </li>
                );
              })}
            </ul>
            {verifyingAnswers[index] && <p className="mcq-feedback">Checking answer...</p>}
            {mcqVerdicts[index] && (
              <p className={`mcq-feedback ${mcqVerdicts[index].isCorrect ? "mcq-feedback-correct" : "mcq-feedback-wrong"}`}>
                {mcqVerdicts[index].isCorrect ? "Answer: Correct" : "Answer: Wrong"}
              </p>
            )}
          </li>
        ))}
      </ol>
      {allAnswered ? (
        <p className="score-board">
          Final Score: {correctCount}/{totalMcqCount}
        </p>
      ) : (
        <p className="score-board">
          Progress: {correctCount} correct out of {answeredCount} answered
        </p>
      )}
    </section>
  );
}

export default McqSection;
