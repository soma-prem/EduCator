function InputSection({
  hasResults,
  textValue,
  onTextChange,
  uploadFile,
  onFileChange,
  canUseText,
  canUseFile,
  canGenerate,
  loadingStudySet,
  onGenerateStudySet,
}) {
  if (hasResults) {
    return null;
  }

  return (
    <>
      <div className="input-cards">
        <article className="input-card">
          <h2>Text Input</h2>
          <p>Paste your content below. File upload will be disabled automatically.</p>
          <div className="input-form">
            <textarea
              value={textValue}
              onChange={onTextChange}
              placeholder="Enter your text here..."
              rows={8}
              disabled={!canUseText}
            />
          </div>
        </article>

        <article className="input-card">
          <h2>File Upload</h2>
          <p>Upload a file (txt, pdf, docx, pptx). Text input will be disabled automatically.</p>
          <div className="input-form">
            <label className={`file-picker ${!canUseFile ? "disabled" : ""}`} htmlFor="file-upload">
              {uploadFile ? uploadFile.name : "Choose file"}
            </label>
            <input
              id="file-upload"
              type="file"
              accept=".txt,.pdf,.docx,.pptx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/pdf,text/plain"
              onChange={onFileChange}
              disabled={!canUseFile}
            />
          </div>
        </article>
      </div>

      <section className="generate-actions">
        <h3>Generate Full Study Set</h3>
        <div className="generate-buttons">
          <button type="button" onClick={onGenerateStudySet} disabled={!canGenerate || loadingStudySet}>
            {loadingStudySet ? "Generating 10 MCQs + 10 Flashcards..." : "Generate 10 MCQs + 10 Flashcards"}
          </button>
        </div>
      </section>
    </>
  );
}

export default InputSection;
