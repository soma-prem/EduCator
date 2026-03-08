function InputSection({ textValue, onTextChange, uploadFile, uploadFileName, onFileChange, canUseText, canUseFile }) {
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
              {uploadFile?.name || uploadFileName || "Choose file"}
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

    </>
  );
}

export default InputSection;
