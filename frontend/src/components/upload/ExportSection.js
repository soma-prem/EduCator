function ExportSection({ hasResults, exportingFormat, onExport, mode = "all" }) {
  if (!hasResults) {
    return null;
  }

  const isBusy = Boolean(exportingFormat);
  const subtitle =
    mode === "mcq"
      ? "Download MCQs as PDF, CSV, or Text."
      : mode === "flashcards"
      ? "Download flashcards as PDF, CSV, or Text."
      : mode === "summary"
      ? "Download summary as PDF, CSV, or Text."
      : mode === "fill_blanks"
      ? "Download fill-in-the-blanks as PDF, CSV, or Text."
      : mode === "true_false"
      ? "Download true/false questions as PDF, CSV, or Text."
      : mode === "match_the_pair"
      ? "Download match-the-pair sets as PDF, CSV, or Text."
      : "Download MCQs/flashcards as PDF, CSV, or Text.";

  return (
    <section className="result-section export-section export-section--compact">
      <h3>Export / Download</h3>
      <p className="export-subtitle">{subtitle}</p>
      <div className="export-buttons export-buttons--pill">
        <button type="button" className="ghost-btn export-btn" onClick={() => onExport("pdf")} disabled={isBusy}>
          {exportingFormat === "pdf" ? "Exporting PDF..." : "Download PDF"}
        </button>
        <button type="button" className="ghost-btn export-btn" onClick={() => onExport("csv")} disabled={isBusy}>
          {exportingFormat === "csv" ? "Exporting CSV..." : "Download CSV"}
        </button>
        <button type="button" className="ghost-btn export-btn" onClick={() => onExport("quiz")} disabled={isBusy}>
          {exportingFormat === "quiz" ? "Exporting Text..." : "Download Text"}
        </button>
      </div>
    </section>
  );
}

export default ExportSection;
