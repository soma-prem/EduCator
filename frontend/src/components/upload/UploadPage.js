import { useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import HistoryPanel from "./HistoryPanel";
import InputSection from "./InputSection";
import McqSection from "./McqSection";
import FlashcardSection from "./FlashcardSection";
import SummarySection from "./SummarySection";
import ActionButtons from "./ActionButtons";

function UploadPage() {
  const [textValue, setTextValue] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [inputMode, setInputMode] = useState("");
  const [mcqs, setMcqs] = useState([]);
  const [mcqSetId, setMcqSetId] = useState("");
  const [mcqVerdicts, setMcqVerdicts] = useState({});
  const [verifyingAnswers, setVerifyingAnswers] = useState({});
  const [flashcards, setFlashcards] = useState([]);
  const [historyItems, setHistoryItems] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [loadingStudySet, setLoadingStudySet] = useState(false);
  const [expandedHistoryId, setExpandedHistoryId] = useState("");
  const [summary, setSummary] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const [audioUrl, setAudioUrl] = useState("");
  const [audioLoading, setAudioLoading] = useState(false);
  const [lastSource, setLastSource] = useState(null);

  useEffect(() => {
    const stopSpeech = () => {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setSpeaking(false);
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopSpeech();
      }
    };

    window.addEventListener("blur", stopSpeech);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("blur", stopSpeech);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const hasText = textValue.trim().length > 0;
  const hasFile = Boolean(uploadFile);
  const canGenerate = hasText || hasFile;
  const hasResults = mcqs.length > 0 || flashcards.length > 0;

  const canUseText = useMemo(() => inputMode !== "file", [inputMode]);
  const canUseFile = useMemo(() => inputMode !== "text", [inputMode]);

  const handleTextChange = (event) => {
    const value = event.target.value;
    setTextValue(value);
    if (value.trim()) {
      setInputMode("text");
      setUploadFile(null);
      return;
    }
    if (!hasFile) {
      setInputMode("");
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setUploadFile(file);
    if (file) {
      setInputMode("file");
      setTextValue("");
      return;
    }
    if (!hasText) {
      setInputMode("");
    }
  };

  const loadHistory = async () => {
    try {
      setHistoryLoading(true);
      const response = await fetch(`${API_BASE}/api/history?limit=25`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Failed to load history");
      }
      setHistoryItems(Array.isArray(data?.items) ? data.items : []);
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to load history");
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleToggleHistory = async () => {
    const next = !showHistory;
    setShowHistory(next);
    setExpandedHistoryId("");
    if (next) {
      await loadHistory();
    }
  };

  const toggleHistoryDetails = (id) => {
    setExpandedHistoryId((prev) => (prev === id ? "" : id));
  };

  const handleClearHistory = async () => {
    try {
      setHistoryLoading(true);
      const response = await fetch(`${API_BASE}/api/history/clear`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Failed to clear history");
      }
      setHistoryItems([]);
      toast.success("History cleared");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to clear history");
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleDeleteHistoryItem = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/api/history/${id}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Failed to delete history item");
      }
      if (!data?.deleted) {
        throw new Error(data?.message || "History item not deleted");
      }
      setHistoryItems((prev) => prev.filter((item) => item.id !== id));
      setExpandedHistoryId((prev) => (prev === id ? "" : prev));
      toast.success("History item deleted");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to delete history item");
    }
  };

  const generateStudySetFromSource = async (source) => {
    const formData = new FormData();
    if (source?.mode === "file" && source?.file) {
      formData.append("file", source.file);
    } else if (source?.mode === "text") {
      formData.append("text", source.text || "");
    } else if (inputMode === "file" && uploadFile) {
      formData.append("file", uploadFile);
    } else {
      formData.append("text", textValue);
    }

    try {
      setLoadingStudySet(true);
      const response = await fetch(`${API_BASE}/api/generate/study-set`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Failed to generate study set");
      }

      const generatedMcqs = Array.isArray(data?.mcqs) ? data.mcqs : [];
      const generatedFlashcards = Array.isArray(data?.flashcards) ? data.flashcards : [];
      if (generatedMcqs.length !== 10 || generatedFlashcards.length !== 10) {
        throw new Error("Server did not return mandatory 10 MCQs and 10 flashcards");
      }

      setMcqs(generatedMcqs);
      setFlashcards(generatedFlashcards);
      setSummary(String(data?.summary || "").trim());
      setAudioUrl("");
      setMcqSetId(data?.mcqSetId || "");
      setMcqVerdicts({});
      setVerifyingAnswers({});
      toast.success("Study set generated: 10 MCQs + 10 Flashcards");
      loadHistory();
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to generate study set");
    } finally {
      setLoadingStudySet(false);
    }
  };

  const handleGenerateStudySet = async () => {
    if (!canGenerate) {
      toast.info("Enter text or upload a file first");
      return;
    }
    await generateStudySetFromSource();
    if (inputMode === "file" && uploadFile) {
      setLastSource({ mode: "file", file: uploadFile });
    } else {
      setLastSource({ mode: "text", text: textValue });
    }
  };

  const handleGenerateOtherResponseSameSource = async () => {
    if (!lastSource) {
      toast.info("No previous source found. Generate once first.");
      return;
    }
    await generateStudySetFromSource(lastSource);
  };

  const extractOptionKey = (value) => {
    const match = String(value || "").trim().match(/^([A-Da-d])(?:[\).\:\-\s]|$)/);
    return match ? match[1].toUpperCase() : "";
  };

  const normalizeOptionText = (value) =>
    String(value || "")
      .trim()
      .replace(/^[A-Da-d](?:[\).\:\-\s]+|$)/, "")
      .toLowerCase();

  const isCorrectOption = (option, answer) => {
    const optionKey = extractOptionKey(option);
    const answerKey = extractOptionKey(answer);
    if (optionKey && answerKey) {
      return optionKey === answerKey;
    }
    const normalizedOption = normalizeOptionText(option);
    const normalizedAnswer = normalizeOptionText(answer);
    return normalizedOption === normalizedAnswer;
  };

  const verifyMcqAnswer = async (questionIndex, selectedAnswer) => {
    if (!mcqSetId) {
      throw new Error("MCQ session missing. Please generate study set again.");
    }
    const response = await fetch(`${API_BASE}/api/verify/mcq`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mcqSetId,
        questionIndex,
        selectedAnswer,
      }),
    });

    if (!response.ok) {
      let message = "Verification failed";
      try {
        const errorJson = await response.json();
        message = errorJson.error || message;
      } catch (_error) {
        const errorText = await response.text();
        if (errorText) {
          message = errorText;
        }
      }
      throw new Error(message);
    }

    return response.json();
  };

  const handleMcqAnswer = async (questionIndex, option) => {
    if (mcqVerdicts[questionIndex] || verifyingAnswers[questionIndex]) {
      return;
    }

    setVerifyingAnswers((prev) => ({ ...prev, [questionIndex]: true }));
    try {
      const mcq = mcqs[questionIndex];
      const verdict = await verifyMcqAnswer(questionIndex, option);
      setMcqVerdicts((prev) => ({
        ...prev,
        [questionIndex]: {
          selectedAnswer: option,
          isCorrect: Boolean(verdict?.is_correct),
          correctAnswer: verdict?.correct_answer || mcq.answer || "",
          correctIndex: Number.isInteger(verdict?.correct_index) ? verdict.correct_index : null,
          correctOption: verdict?.correct_option || "",
          explanation: verdict?.explanation || "Checked with stored answer key.",
        },
      }));
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to verify answer");
    } finally {
      setVerifyingAnswers((prev) => {
        const next = { ...prev };
        delete next[questionIndex];
        return next;
      });
    }
  };

  const answeredCount = Object.keys(mcqVerdicts).length;
  const totalMcqCount = mcqs.length;
  const correctCount = Object.values(mcqVerdicts).reduce(
    (score, verdict) => score + (verdict?.isCorrect ? 1 : 0),
    0
  );
  const allAnswered = totalMcqCount > 0 && answeredCount === totalMcqCount;

  const saveCurrentSession = async () => {
    const payload = {
      sourceType: inputMode || (uploadFile ? "file" : "text"),
      sourcePreview: inputMode === "text" ? textValue.slice(0, 300) : uploadFile?.name || "",
      hadMcqs: mcqs.length > 0,
      hadFlashcards: flashcards.length > 0,
      mcqTotal: totalMcqCount,
      mcqCorrect: correctCount,
      mcqs,
      flashcards,
      summary,
    };
    const response = await fetch(`${API_BASE}/api/history/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let message = "Failed to store session";
      try {
        const err = await response.json();
        message = err.error || message;
      } catch (_error) {
        const text = await response.text();
        if (text) {
          message = text;
        }
      }
      throw new Error(message);
    }
    const result = await response.json();
    if (!result?.stored) {
      throw new Error(result?.error || "History not stored. Check Firebase configuration.");
    }
  };

  const handleSaveAndGenerateOtherSource = async () => {
    try {
      await saveCurrentSession();
      toast.success("Saved. Ready for another source.");
      await loadHistory();
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setSpeaking(false);
      setAudioUrl("");
      setTextValue("");
      setUploadFile(null);
      setInputMode("");
      setMcqs([]);
      setMcqSetId("");
      setMcqVerdicts({});
      setVerifyingAnswers({});
      setFlashcards([]);
      setSummary("");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to save current session");
    }
  };

  const handleGenerateOtherSource = async () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setSpeaking(false);
    setAudioUrl("");
    setTextValue("");
    setUploadFile(null);
    setInputMode("");
    setMcqs([]);
    setMcqSetId("");
    setMcqVerdicts({});
    setVerifyingAnswers({});
    setFlashcards([]);
    setSummary("");
  };

  const handleSpeakSummary = () => {
    if (!summary) {
      toast.info("Summary is empty");
      return;
    }
    if (!("speechSynthesis" in window)) {
      toast.error("Text-to-speech is not supported in this browser");
      return;
    }
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(summary);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  const handleGenerateAudio = async () => {
    if (!summary) {
      toast.info("Summary is empty");
      return;
    }
    try {
      setAudioLoading(true);
      const response = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: summary }),
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
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to generate audio");
    } finally {
      setAudioLoading(false);
    }
  };

  return (
    <main className="upload-page">
      <div className="home-bots" aria-hidden="true">
        <div className="boat-group">
          <img src="/blue.png" alt="" className="bot boat boat-blue" />
        </div>
      </div>
      <section className="upload-card upload-layout">
        <header className="upload-header">
          <button type="button" className="history-btn" onClick={handleToggleHistory}>
            {showHistory ? "Hide History" : "History"}
          </button>
          <h1>Upload Workspace</h1>
          <p>Choose text input or file upload to continue.</p>
        </header>

        {showHistory && (
          <HistoryPanel
            historyItems={historyItems}
            historyLoading={historyLoading}
            expandedHistoryId={expandedHistoryId}
            onClearHistory={handleClearHistory}
            onToggleDetails={toggleHistoryDetails}
            onDeleteItem={handleDeleteHistoryItem}
          />
        )}

        {!showHistory && (
          <>
            <InputSection
              hasResults={hasResults}
              textValue={textValue}
              onTextChange={handleTextChange}
              uploadFile={uploadFile}
              onFileChange={handleFileChange}
              canUseText={canUseText}
              canUseFile={canUseFile}
              canGenerate={canGenerate}
              loadingStudySet={loadingStudySet}
              onGenerateStudySet={handleGenerateStudySet}
            />

            <McqSection
              mcqs={mcqs}
              mcqVerdicts={mcqVerdicts}
              verifyingAnswers={verifyingAnswers}
              onAnswer={handleMcqAnswer}
              isCorrectOption={isCorrectOption}
              allAnswered={allAnswered}
              correctCount={correctCount}
              answeredCount={answeredCount}
              totalMcqCount={totalMcqCount}
            />

            <FlashcardSection flashcards={flashcards} />

            <SummarySection
              summary={summary}
              speaking={speaking}
              onSpeak={handleSpeakSummary}
              audioLoading={audioLoading}
              onGenerateAudio={handleGenerateAudio}
              audioUrl={audioUrl}
            />

            <ActionButtons
              hasResults={hasResults}
              loadingStudySet={loadingStudySet}
              onGenerateOtherResponseSameSource={handleGenerateOtherResponseSameSource}
              onGenerateOtherSource={handleGenerateOtherSource}
              onSaveAndGenerateOtherSource={handleSaveAndGenerateOtherSource}
            />
          </>
        )}
      </section>
    </main>
  );
}

export default UploadPage;
