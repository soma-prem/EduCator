import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import { auth } from "../../firebase";
import McqSection from "./McqSection";
import FlashcardSection from "./FlashcardSection";
import ExportSection from "./ExportSection";
import SummarySection from "./SummarySection";
import KnowledgeGapSection from "./KnowledgeGapSection";
import DifficultySelect, { normalizeDifficulty } from "./DifficultySelect";
import SpacedPlanSection from "./SpacedPlanSection";
import VoiceTutorSection from "./VoiceTutorSection";
import usePremium from "../../premium/usePremium";

function StudySetPage({ mode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const premium = usePremium();
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
  const savedStateRaw = (() => {
    try {
      return localStorage.getItem("educator_study_set") || sessionStorage.getItem("educator_study_set");
    } catch (_error) {
      return sessionStorage.getItem("educator_study_set");
    }
  })();
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
  const [mcqs, setMcqs] = useState(normalizeArray(routeState?.mcqs));
  const [flashcards, setFlashcards] = useState(normalizeArray(routeState?.flashcards));
  const [summary] = useState(String(routeState?.summary || "").trim());
  const [mcqSetId, setMcqSetId] = useState(String(routeState?.mcqSetId || "").trim());
  const [sourceType] = useState(String(routeState?.sourceType || "").trim());
  const [sourceText] = useState(String(routeState?.sourceText || "").trim());
  const [sourceFileId] = useState(String(routeState?.sourceFileId || "").trim());
  const [difficultyByMode, setDifficultyByMode] = useState(() => {
    const saved = routeState?.difficultyByMode && typeof routeState.difficultyByMode === "object" ? routeState.difficultyByMode : {};
    return {
      mcq: normalizeDifficulty(saved.mcq || saved.mcqs || "medium"),
      flashcards: normalizeDifficulty(saved.flashcards || "medium"),
    };
  });

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
  const [flashcardKnown, setFlashcardKnown] = useState({});
  const [spacedBoxes, setSpacedBoxes] = useState(routeState?.spacedBoxes || {});
  const [spacedSchedule, setSpacedSchedule] = useState(routeState?.spacedSchedule || []);
  const [topics, setTopics] = useState(routeState?.topics || []);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [revisionData, setRevisionData] = useState(null);
  const [revisionLoading, setRevisionLoading] = useState(false);
  const [voiceTutorOpen, setVoiceTutorOpen] = useState(false);

  const handleUpgrade = () => navigate("/premium");

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
  const flashKnownCount = Object.values(flashcardKnown || {}).filter((value) => value === true).length;
  const flashTotalCount = flashcards.length;
  const mcqAccuracy = answeredCount > 0 ? correctCount / answeredCount : 0;
  const flashAccuracy = flashTotalCount > 0 ? flashKnownCount / flashTotalCount : 0;
  const userId = auth?.currentUser?.uid || "";
  const planId =
    String(mcqSetId || sourceFileId || (sourceText ? `text:${sourceText.slice(0, 32)}` : "default")).trim() || "default";

  const currentMode = lockedMode ? initialTab : activeTab;
  const selectedDifficulty = difficultyByMode[currentMode] || "medium";

  useEffect(() => {
    fetchTopics();
    if (flashcards.length > 0) {
      syncSpacedPlan(flashcardKnown);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flashcards]);

  useEffect(() => {
    const loadPlan = async () => {
      if (!userId || !planId) return;
      try {
        const response = await fetch(`${API_BASE}/api/spaced/load`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ userId, planId }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          return;
        }
        if (data?.boxes) setSpacedBoxes(data.boxes);
        if (Array.isArray(data?.schedule)) setSpacedSchedule(data.schedule);
        updateSessionStorage({
          spacedBoxes: data?.boxes || {},
          spacedSchedule: Array.isArray(data?.schedule) ? data.schedule : [],
        });
      } catch (_err) {
        // ignore load failure silently
      }
    };
    loadPlan();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, planId]);

  useEffect(() => {
    if (answeredCount === 0) return;
    let suggestion = "medium";
    if (mcqAccuracy >= 0.8) {
      suggestion = "hard";
    } else if (mcqAccuracy <= 0.5) {
      suggestion = "easy";
    }
    setDifficultyByMode((prev) => {
      if (prev.mcq === suggestion) return prev;
      toast.info(`Adaptive difficulty set to ${suggestion} for next MCQ generation`);
      return { ...prev, mcq: suggestion };
    });
  }, [answeredCount, mcqAccuracy]);

  useEffect(() => {
    if (flashTotalCount === 0) return;
    if (flashKnownCount === 0) return;
    let suggestion = "medium";
    const accuracy = flashAccuracy;
    if (accuracy >= 0.85) suggestion = "hard";
    else if (accuracy <= 0.5) suggestion = "easy";
    setDifficultyByMode((prev) => {
      if (prev.flashcards === suggestion) return prev;
      toast.info(`Adaptive difficulty set to ${suggestion} for next flashcard generation`);
      return { ...prev, flashcards: suggestion };
    });
  }, [flashAccuracy, flashKnownCount, flashTotalCount]);

  const updateSessionStorage = (partial) => {
    const savedRaw = (() => {
      try {
        return localStorage.getItem("educator_study_set") || sessionStorage.getItem("educator_study_set") || "";
      } catch (_error) {
        return sessionStorage.getItem("educator_study_set") || "";
      }
    })();
    let saved = {};
    if (savedRaw) {
      try {
        saved = JSON.parse(savedRaw) || {};
      } catch (_error) {
        saved = {};
      }
    }
    const next = { ...saved, ...partial };
    try {
      localStorage.setItem("educator_study_set", JSON.stringify(next));
    } catch (_error) {}
    sessionStorage.setItem("educator_study_set", JSON.stringify(next));
  };

  const syncSpacedPlan = async (nextKnownMap) => {
    if (!flashcards || flashcards.length === 0) return;
    const payload = {
      flashcards,
      marks: Object.entries(nextKnownMap || {}).reduce((acc, [index, known]) => {
        acc[String(index)] = known ? "known" : "review";
        return acc;
      }, {}),
      previous: spacedBoxes,
    };
    try {
      const response = await fetch(`${API_BASE}/api/spaced/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Spaced repetition scheduling failed");
      }
      const boxes = data?.boxes || {};
      const schedule = Array.isArray(data?.schedule) ? data.schedule : [];
      setSpacedBoxes(boxes);
      setSpacedSchedule(schedule);
      updateSessionStorage({ spacedBoxes: boxes, spacedSchedule: schedule });
      if (userId) {
        try {
          await fetch(`${API_BASE}/api/spaced/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ userId, planId, boxes, schedule }),
          });
        } catch (_err) {
          // non-blocking
        }
      }
    } catch (error) {
      toast.error(error?.message || "Unable to schedule reviews");
    }
  };

  const fetchTopics = async () => {
    if (topicsLoading) return;
    if (topics && topics.length > 0) return;
    const form = buildSourceFormData(selectedDifficulty);
    if (!form) return;
    setTopicsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/analyze/topics`, { method: "POST", body: form });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Topic extraction failed");
      }
      const nextTopics = Array.isArray(data?.topics) ? data.topics : [];
      setTopics(nextTopics);
      updateSessionStorage({ topics: nextTopics });
    } catch (error) {
      console.warn(error);
    } finally {
      setTopicsLoading(false);
    }
  };

  const buildSourceFormData = (difficulty) => {
    const formData = new FormData();
    if (Array.isArray(routeState?.sources) && routeState.sources.length > 0) {
      let hasAny = false;
      routeState.sources.forEach((item) => {
        if (item?.mode === "file" && item?.fileId) {
          formData.append("fileId", item.fileId);
          hasAny = true;
        } else if (item?.mode === "text" && item?.text) {
          formData.append("text", item.text);
          hasAny = true;
        }
      });
      if (hasAny) {
        formData.append("difficulty", normalizeDifficulty(difficulty));
        return formData;
      }
    }
    if (sourceFileId) {
      formData.append("fileId", sourceFileId);
    } else if (sourceText) {
      formData.append("text", sourceText);
    } else if (sourceType === "text" && routeState?.sourceText) {
      formData.append("text", String(routeState.sourceText));
    } else if (routeState?.sourceFileId) {
      formData.append("fileId", String(routeState.sourceFileId));
    } else {
      return null;
    }
    formData.append("difficulty", normalizeDifficulty(difficulty));
    return formData;
  };

  const regenerateForDifficulty = async (nextDifficulty) => {
    const difficulty = normalizeDifficulty(nextDifficulty);
    const baseForm = buildSourceFormData(difficulty);
    if (!baseForm) {
      toast.error("Source missing. Go back to Upload and generate again.");
      return;
    }

    setRegenerating(true);
    try {
      if (currentMode === "mcq") {
        const formData = baseForm;
        formData.append("tool", "mcq");
        formData.append("count", "12");
        const response = await fetch(`${API_BASE}/api/tools/generate`, { method: "POST", body: formData });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data?.error || "Failed to regenerate MCQs");
        }
        const nextMcqs = Array.isArray(data?.mcqs) ? data.mcqs : [];
        if (nextMcqs.length === 0) {
          throw new Error("Server returned no MCQs");
        }
        const nextSetId = String(data?.mcqSetId || "").trim();
        setMcqs(nextMcqs);
        setMcqSetId(nextSetId);
        setMcqVerdicts({});
        setFlashcardKnown({});
        setKnowledgeGapResult(null);
        updateSessionStorage({
          mcqs: nextMcqs,
          mcqSetId: nextSetId,
          difficultyByMode: { ...difficultyByMode, mcq: difficulty },
        });
        return;
      }

      if (currentMode === "flashcards") {
        const formData = baseForm;
        formData.append("tool", "flashcards");
        formData.append("count", "12");
        const response = await fetch(`${API_BASE}/api/tools/generate`, { method: "POST", body: formData });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data?.error || "Failed to regenerate flashcards");
        }
        const nextFlashcards = Array.isArray(data?.flashcards) ? data.flashcards : [];
        if (nextFlashcards.length === 0) {
          throw new Error("Server returned no flashcards");
        }
        setFlashcards(nextFlashcards);
        setFlashcardKnown({});
        setSpacedBoxes({});
        setSpacedSchedule([]);
        setKnowledgeGapResult(null);
        updateSessionStorage({
          flashcards: nextFlashcards,
          spacedBoxes: {},
          spacedSchedule: [],
          difficultyByMode: { ...difficultyByMode, flashcards: difficulty },
        });
      }
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to regenerate");
    } finally {
      setRegenerating(false);
    }
  };

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

  const handleSmartRevision = async () => {
    if (revisionLoading) return;
    setRevisionLoading(true);
    try {
      const attempts = Object.keys(mcqVerdicts).reduce((acc, key) => {
        const verdict = mcqVerdicts[key];
        if (verdict?.selectedAnswer) acc[key] = verdict.selectedAnswer;
        return acc;
      }, {});
      const payload = {
        mcqs,
        attempts,
        flashcards,
        spacedSchedule,
      };
      const response = await fetch(`${API_BASE}/api/revision/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Revision failed");
      }
      setRevisionData(data);
      toast.success("Smart Revision ready");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Smart Revision failed");
    } finally {
      setRevisionLoading(false);
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
      const token = auth.currentUser ? await auth.currentUser.getIdToken() : "";
      const response = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
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
      setKnowledgeGapLoading(true);
      const payload =
        currentMode === "mcq"
          ? {
              mode: "mcq",
              items: mcqs,
              attempts: Object.keys(mcqVerdicts).reduce((acc, indexKey) => {
                const selected = mcqVerdicts[indexKey]?.selectedAnswer;
                if (selected) {
                  acc[indexKey] = selected;
                }
                return acc;
              }, {}),
            }
          : {
              mode: "flashcards",
              items: flashcards,
              attempts: flashcardKnown,
            };

      const selectedAnswers = {};
      Object.keys(payload.attempts || {}).forEach((key) => {
        selectedAnswers[key] = payload.attempts[key];
      });

      const token = auth.currentUser ? await auth.currentUser.getIdToken() : "";
      const response = await fetch(`${API_BASE}/api/recommend/knowledge-gaps/content`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          threshold: 0.6,
          language: ttsLanguage,
          mode: payload.mode,
          items: payload.items,
          attempts: selectedAnswers,
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
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <DifficultySelect
              value={selectedDifficulty}
              onChange={(value) => {
                const next = normalizeDifficulty(value);
                setDifficultyByMode((prev) => ({ ...prev, [currentMode]: next }));
                regenerateForDifficulty(next);
              }}
              disabled={regenerating}
            />
            {/* Smart Revision and Voice Tutor controls removed for MCQ generation page */}
          </div>
        </header>

        <ExportSection
          hasResults={mcqs.length > 0 || flashcards.length > 0}
          exportingFormat={exportingFormat}
          onExport={handleExport}
          mode={lockedMode ? initialTab : "all"}
        />

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
            <FlashcardSection
              flashcards={filteredFlashcards}
              knownMap={flashcardKnown}
              onMark={(index, known) => {
                setFlashcardKnown((prev) => {
                  const next = { ...prev, [index]: known };
                  syncSpacedPlan(next);
                  return next;
                });
              }}
            />
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
        topics={topics}
        topicsLoading={topicsLoading}
        audioLocked={!premium.canUse("audio_summary")}
        onUpgrade={handleUpgrade}
      />
    )}

        <SpacedPlanSection
          schedule={spacedSchedule}
          onReset={async () => {
            setSpacedBoxes({});
            setSpacedSchedule([]);
            updateSessionStorage({ spacedBoxes: {}, spacedSchedule: [] });
            if (userId) {
              try {
                await fetch(`${API_BASE}/api/spaced/save`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ userId, planId, boxes: {}, schedule: [] }),
                });
              } catch (_err) {}
            }
          }}
        />

        <KnowledgeGapSection
          result={knowledgeGapResult}
          loading={knowledgeGapLoading}
          onAnalyze={handleAnalyzeKnowledgeGaps}
          locked={!premium.canUse("knowledge_gap")}
          onUpgrade={handleUpgrade}
        />

        {revisionData && (
          <section className="result-section">
            <h3>Smart Revision</h3>
            {revisionData.weakTopics && revisionData.weakTopics.length > 0 && (
              <ul className="result-options">
                {revisionData.weakTopics.map((t) => (
                  <li key={t.topic}>
                    {t.topic} — accuracy {(t.accuracy * 100).toFixed(0)}% ({t.attempted} attempts)
                  </li>
                ))}
              </ul>
            )}
            {revisionData.flashcards && revisionData.flashcards.length > 0 && (
              <FlashcardSection flashcards={revisionData.flashcards} />
            )}
            {revisionData.quiz && revisionData.quiz.length > 0 && (
              <McqSection
                mcqs={revisionData.quiz}
                mcqVerdicts={{}}
                verifyingAnswers={{}}
                onAnswer={() => {}}
                isCorrectOption={() => false}
                allAnswered={false}
                correctCount={0}
                answeredCount={0}
                totalMcqCount={revisionData.quiz.length}
              />
            )}
          </section>
        )}

        {voiceTutorOpen && <VoiceTutorSection apiBase={API_BASE} />}

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
