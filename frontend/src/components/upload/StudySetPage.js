import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import McqSection from "./McqSection";
import FlashcardSection from "./FlashcardSection";
import ExportSection from "./ExportSection";
import SummarySection from "./SummarySection";
import KnowledgeGapSection from "./KnowledgeGapSection";

function StudySetPage({ mode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const ttsLanguages = [
    { value: "en", label: "English" },
    { value: "hi", label: "Hindi" },
    { value: "es", label: "Spanish" },
    { value: "fr", label: "French" },
    { value: "de", label: "German" },
    { value: "it", label: "Italian" },
    { value: "pt", label: "Portuguese" },
    { value: "ja", label: "Japanese" },
  ];
  const savedStateRaw = sessionStorage.getItem("educator_study_set");
  let savedState = null;
  if (savedStateRaw) {
    try {
      savedState = JSON.parse(savedStateRaw);
    } catch (_error) {
      savedState = null;
    }
  }
  const routeState = location.state || savedState || {};
  const normalizeArray = (value) => {
    if (Array.isArray(value)) return value;
    if (typeof value === "string") {
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : [];
      } catch (_error) {
        return [];
      }
    }
    return [];
  };
  const [mcqs] = useState(normalizeArray(routeState?.mcqs));
  const [flashcards] = useState(normalizeArray(routeState?.flashcards));
  const [summary] = useState(String(routeState?.summary || "").trim());
  const [mcqSetId] = useState(String(routeState?.mcqSetId || "").trim());
  const [sourceType] = useState(String(routeState?.sourceType || "").trim());
  const [sourcePreview] = useState(String(routeState?.sourcePreview || "").trim());

  const lockedMode = mode === "mcq" || mode === "flashcards";
  const initialTab = mode === "flashcards" ? "flashcards" : "mcq";
  const [activeTab, setActiveTab] = useState(initialTab);
  const [mcqVerdicts, setMcqVerdicts] = useState({});
  const [verifyingAnswers, setVerifyingAnswers] = useState({});
  const [exportingFormat, setExportingFormat] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [audioLoading, setAudioLoading] = useState(false);
  const [ttsLanguage, setTtsLanguage] = useState("en");
  const [knowledgeGapLoading, setKnowledgeGapLoading] = useState(false);
  const [knowledgeGapResult, setKnowledgeGapResult] = useState(null);
  const [savingHistory, setSavingHistory] = useState(false);

  const filteredMcqPairs = useMemo(() => mcqs.map((item, index) => ({ item, index })), [mcqs]);
  const filteredFlashcards = useMemo(() => flashcards, [flashcards]);

  const extractOptionKey = (value) => {
    const match = String(value || "").trim().match(/^([A-Da-d])(?:[).:\s-]|$)/);
    return match ? match[1].toUpperCase() : "";
  };

  const normalizeOptionText = (value) =>
    String(value || "")
      .trim()
      .replace(/^[A-Da-d](?:[).:\s-]+|$)/, "")
      .toLowerCase();

  const isCorrectOption = (option, answer) => {
    const optionKey = extractOptionKey(option);
    const answerKey = extractOptionKey(answer);
    if (optionKey && answerKey) {
      return optionKey === answerKey;
    }
    return normalizeOptionText(option) === normalizeOptionText(answer);
  };

  const verifyMcqAnswer = async (questionIndex, selectedAnswer) => {
    if (!mcqSetId) {
      throw new Error("MCQ session missing. Generate again from upload page.");
    }
    const response = await fetch(`${API_BASE}/api/verify/mcq`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mcqSetId, questionIndex, selectedAnswer }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data?.error || "Verification failed");
    }
    return response.json();
  };

  const handleMcqAnswer = async (visibleIndex, option) => {
    const originalIndex = filteredMcqPairs[visibleIndex]?.index;
    if (!Number.isInteger(originalIndex)) {
      return;
    }
    if (mcqVerdicts[originalIndex] || verifyingAnswers[originalIndex]) {
      return;
    }

    setVerifyingAnswers((prev) => ({ ...prev, [originalIndex]: true }));
    try {
      const mcq = mcqs[originalIndex];
      const verdict = await verifyMcqAnswer(originalIndex, option);
      setMcqVerdicts((prev) => ({
        ...prev,
        [originalIndex]: {
          selectedAnswer: option,
          isCorrect: Boolean(verdict?.is_correct),
          correctAnswer: verdict?.correct_answer || mcq.answer || "",
          correctIndex: Number.isInteger(verdict?.correct_index) ? verdict.correct_index : null,
          explanation: verdict?.explanation || mcq.explanation || "",
        },
      }));
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to verify answer");
    } finally {
      setVerifyingAnswers((prev) => {
        const next = { ...prev };
        delete next[originalIndex];
        return next;
      });
    }
  };

  const localVerdicts = useMemo(() => {
    const next = {};
    filteredMcqPairs.forEach((entry, visibleIndex) => {
      if (mcqVerdicts[entry.index]) {
        next[visibleIndex] = mcqVerdicts[entry.index];
      }
    });
    return next;
  }, [filteredMcqPairs, mcqVerdicts]);

  const localVerifying = useMemo(() => {
    const next = {};
    filteredMcqPairs.forEach((entry, visibleIndex) => {
      if (verifyingAnswers[entry.index]) {
        next[visibleIndex] = true;
      }
    });
    return next;
  }, [filteredMcqPairs, verifyingAnswers]);

  const localMcqs = filteredMcqPairs.map((entry) => entry.item);
  const answeredCount = Object.keys(localVerdicts).length;
  const totalCount = localMcqs.length;
  const correctCount = Object.values(localVerdicts).reduce((acc, item) => acc + (item?.isCorrect ? 1 : 0), 0);
  const allAnswered = totalCount > 0 && answeredCount === totalCount;
  const overallCorrectCount = Object.values(mcqVerdicts).reduce((acc, item) => acc + (item?.isCorrect ? 1 : 0), 0);

  const handleExport = async (format) => {
    try {
      setExportingFormat(format);
      const response = await fetch(`${API_BASE}/api/export/study-set/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "educator_study_set",
          mcqs: lockedMode && initialTab === "flashcards" ? [] : mcqs,
          flashcards: lockedMode && initialTab === "mcq" ? [] : flashcards,
          summary,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.error || "Export failed");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const fallback = `study_set.${format === "quiz" ? "quiz.txt" : format}`;
      const disposition = response.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="([^"]+)"/i);
      const filename = match?.[1] || fallback;

      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success(`Downloaded ${filename}`);
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Export failed");
    } finally {
      setExportingFormat("");
    }
  };

  const handleSpeakSummary = () => {
    if (!summary) {
      toast.info("Summary is empty");
      return "";
    }
    return handleGenerateAudio();
  };

  const handleGenerateAudio = async () => {
    if (!summary) {
      toast.info("Summary is empty");
      return "";
    }
    try {
      setAudioLoading(true);
      const response = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: summary, language: ttsLanguage, translate: true }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.error || "Failed to generate audio");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      setAudioUrl(url);
      toast.success("Audio generated");
      return url;
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to generate audio");
      return "";
    } finally {
      setAudioLoading(false);
    }
  };

  const handleAnalyzeKnowledgeGaps = async () => {
    try {
      if (!mcqSetId) {
        toast.error("MCQ session missing. Generate again.");
        return;
      }
      setKnowledgeGapLoading(true);
      const selectedAnswers = {};
      Object.keys(mcqVerdicts).forEach((indexKey) => {
        const selected = mcqVerdicts[indexKey]?.selectedAnswer;
        if (selected) {
          selectedAnswers[indexKey] = selected;
        }
      });

      const response = await fetch(`${API_BASE}/api/recommend/knowledge-gaps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mcqSetId,
          selectedAnswers,
          threshold: 0.6,
          language: ttsLanguage,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Failed to analyze knowledge gaps");
      }
      setKnowledgeGapResult(data);
      if (Array.isArray(data?.weakTopics) && data.weakTopics.length > 0) {
        toast.success("Weak topics detected and study recommendations generated");
      } else {
        toast.success("No weak topics detected");
      }
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to analyze knowledge gaps");
    } finally {
      setKnowledgeGapLoading(false);
    }
  };


  const handleSaveHistory = async () => {
    try {
      setSavingHistory(true);
      const payload = {
        sourceType: sourceType || "text",
        sourcePreview: sourcePreview || "",
        hadMcqs: mcqs.length > 0,
        hadFlashcards: flashcards.length > 0,
        mcqTotal: mcqs.length,
        mcqCorrect: overallCorrectCount,
        mcqs,
        flashcards,
        summary,
      };
      const response = await fetch(`${API_BASE}/api/history/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Failed to save history");
      }
      if (!data?.stored) {
        throw new Error(data?.error || "History not stored");
      }
      toast.success("Saved to history");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to save history");
    } finally {
      setSavingHistory(false);
    }
  };

  if (mcqs.length === 0 && flashcards.length === 0) {
    return (
      <main className="upload-page">
        <section className="upload-card upload-layout">
          <header className="upload-header">
            <h1>No Study Set Found</h1>
            <p>Generate a study set first from Upload page.</p>
          </header>
          <div style={{ textAlign: "center" }}>
            <button type="button" onClick={() => navigate("/uplod")}>
              Go to Upload
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="upload-page">
      <section className="upload-card upload-layout">
        <header className="upload-header">
          <h1>Study Set Workspace</h1>
          <p>Review MCQs, flashcards, and summaries from your study set.</p>
        </header>

        {!lockedMode && (
          <div className="study-tabs">
            <button
              type="button"
              className={`study-tab ${activeTab === "mcq" ? "study-tab-active" : ""}`}
              onClick={() => setActiveTab("mcq")}
            >
              MCQ
            </button>
            <button
              type="button"
              className={`study-tab ${activeTab === "flashcards" ? "study-tab-active" : ""}`}
              onClick={() => setActiveTab("flashcards")}
            >
              Flashcards
            </button>
          </div>
        )}

        {(lockedMode ? initialTab === "mcq" : activeTab === "mcq") ? (
          localMcqs.length > 0 ? (
            <McqSection
              mcqs={localMcqs}
              mcqVerdicts={localVerdicts}
              verifyingAnswers={localVerifying}
              onAnswer={handleMcqAnswer}
              isCorrectOption={isCorrectOption}
              allAnswered={allAnswered}
              correctCount={correctCount}
              answeredCount={answeredCount}
              totalMcqCount={totalCount}
            />
          ) : (
            <section className="result-section">
              <h3>MCQs</h3>
              <p className="topic-empty-text">No MCQs found.</p>
            </section>
          )
        ) : (
          filteredFlashcards.length > 0 ? (
            <FlashcardSection flashcards={filteredFlashcards} />
          ) : (
            <section className="result-section">
              <h3>Flashcards</h3>
              <p className="topic-empty-text">No flashcards found.</p>
            </section>
          )
        )}

      {!lockedMode && (
        <SummarySection
          summary={summary}
          onSpeak={handleSpeakSummary}
          audioLoading={audioLoading}
          onGenerateAudio={handleGenerateAudio}
          audioUrl={audioUrl}
          ttsLanguage={ttsLanguage}
          onTtsLanguageChange={setTtsLanguage}
          ttsLanguages={ttsLanguages}
        />
      )}

        <KnowledgeGapSection
          result={knowledgeGapResult}
          loading={knowledgeGapLoading}
          onAnalyze={handleAnalyzeKnowledgeGaps}
        />

        <ExportSection
          hasResults={mcqs.length > 0 || flashcards.length > 0}
          exportingFormat={exportingFormat}
          onExport={handleExport}
          mode={lockedMode ? initialTab : "all"}
        />

        <div className="other-source-wrap dual-actions" style={{ marginTop: "0.9rem" }}>
          <button type="button" className="ghost-btn" onClick={() => navigate("/uplod")}>
            Back to Upload
          </button>
        </div>
      </section>
    </main>
  );
}

export default StudySetPage;
