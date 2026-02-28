function ActionButtons({
  hasResults,
  loadingStudySet,
  onGenerateOtherResponseSameSource,
  onGenerateOtherSource,
  onSaveAndGenerateOtherSource,
}) {
  if (!hasResults) {
    return null;
  }

  return (
    <div className="other-source-wrap dual-actions">
      <button
        type="button"
        className="icon-action-btn"
        onClick={onGenerateOtherResponseSameSource}
        disabled={loadingStudySet}
        title="Generate another set from the same source"
        aria-label="Generate another response for the same source"
      >
        <img src="/regenerate.png" alt="" className="icon-action-img" />
      </button>
      <button
        type="button"
        className="icon-action-btn"
        onClick={onGenerateOtherSource}
        title="Start with a new source (no save)"
        aria-label="Generate for other source"
      >
        <img src="/unsave.png" alt="" className="icon-action-img" />
      </button>
      <button
        type="button"
        className="icon-action-btn"
        onClick={onSaveAndGenerateOtherSource}
        title="Save and start a new source"
        aria-label="Save and generate other source"
      >
        <img src="/save.png" alt="" className="icon-action-img" />
      </button>
    </div>
  );
}

export default ActionButtons;
