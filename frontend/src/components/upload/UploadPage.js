import { useEffect, useMemo, useState } from "react";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../../config/api";
import InputSection from "./InputSection";
import VoiceQASection from "./VoiceQASection";

function UploadPage({ user }) {
  const displayName =
    user?.displayName ||
    user?.email?.split("@")[0] ||
    "Learner";
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
  const [textValue, setTextValue] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [storedFileId, setStoredFileId] = useState("");
  const [storedFileName, setStoredFileName] = useState("");
  const [inputMode, setInputMode] = useState("");
  const [mcqs, setMcqs] = useState([]);
  const [mcqSetId, setMcqSetId] = useState("");
  const [mcqVerdicts, setMcqVerdicts] = useState({});
  const [verifyingAnswers, setVerifyingAnswers] = useState({});
  const [flashcards, setFlashcards] = useState([]);
  const [loadingStudySet, setLoadingStudySet] = useState(false);
  const [summary, setSummary] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [audioLoading, setAudioLoading] = useState(false);
  const [summaryGenerating, setSummaryGenerating] = useState(false);
  const [ttsLanguage, setTtsLanguage] = useState("en");
  const [lastSource, setLastSource] = useState(null);
  const [exportingFormat, setExportingFormat] = useState("");
  const [ragQuestion, setRagQuestion] = useState("");
  const [ragAnswer, setRagAnswer] = useState("");
  const [ragLoading, setRagLoading] = useState(false);
  const [aiGuideMode, setAiGuideMode] = useState("text");
  const [voiceQuestion, setVoiceQuestion] = useState("");
  const [voiceAnswer, setVoiceAnswer] = useState("");
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceAnswerAudioUrl, setVoiceAnswerAudioUrl] = useState("");
  const [recognizer, setRecognizer] = useState(null);
  const [sourceModalOpen, setSourceModalOpen] = useState(false);
  const [sources, setSources] = useState([]);
  const [mcqGenerating, setMcqGenerating] = useState(false);
  const [flashGenerating, setFlashGenerating] = useState(false);
  const [savingSession, setSavingSession] = useState(false);
  const [mcqReady, setMcqReady] = useState(false);
  const [flashReady, setFlashReady] = useState(false);
  const [mcqPayload, setMcqPayload] = useState(null);
  const [flashPayload, setFlashPayload] = useState(null);

  const persistSourceSession = (sourceType, sourcePreview, sourceText = "", sourceFileId = "", sourceFileName = "") => {
    const payload = {
      sourceType,
      sourcePreview,
      sourceText,
      sourceFileId,
      sourceFileName,
      mcqs: [],
      flashcards: [],
      summary: "",
      mcqSetId: "",
    };
    sessionStorage.setItem("educator_study_set", JSON.stringify(payload));
  };

  const resetGeneratedOutputs = () => {
    setMcqs([]);
    setFlashcards([]);
    setSummary("");
    setMcqSetId("");
    setMcqVerdicts({});
    setVerifyingAnswers({});
    setMcqReady(false);
    setFlashReady(false);
    setMcqPayload(null);
    setFlashPayload(null);
    setAudioUrl("");
  };

  useEffect(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      return;
    }
    const rec = new Recognition();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (event) => {
      const text = String(event.results?.[0]?.[0]?.transcript || "").trim();
      if (text) {
        setVoiceQuestion(text);
      }
      setListening(false);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    setRecognizer(rec);
  }, []);

  const getReadableErrorMessage = (error, fallbackMessage) => {
    const raw = String(error?.message || "").toLowerCase();
    if (raw.includes("failed to fetch") || raw.includes("networkerror") || raw.includes("load failed")) {
      return `Cannot reach backend at ${API_BASE}. Start backend server and verify CORS/API URL.`;
    }
    return error?.message || fallbackMessage;
  };


  const hasText = textValue.trim().length > 0;
  const hasFile = Boolean(uploadFile) || Boolean(storedFileId);
  const canGenerate = hasText || hasFile;
  const hasResults = mcqs.length > 0 || flashcards.length > 0;
  const hasSummary = summary.trim().length > 0;
  const hasSource =
    sources.length > 0 ||
    (inputMode === "file" && (uploadFile || storedFileId)) ||
    (inputMode === "text" && textValue.trim().length > 0);

  const canUseText = useMemo(() => inputMode !== "file", [inputMode]);
  const canUseFile = useMemo(() => inputMode !== "text", [inputMode]);

  const handleTextChange = (event) => {
    const value = event.target.value;
    setTextValue(value);
    if (value.trim()) {
      setInputMode("text");
      setUploadFile(null);
      setStoredFileId("");
      setStoredFileName("");
      resetGeneratedOutputs();
      persistSourceSession("text", value.slice(0, 300), value);
      return;
    }
    if (!hasFile) {
      setInputMode("");
    }
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0] || null;
    setUploadFile(file);
    if (file) {
      setInputMode("file");
      setTextValue("");
      resetGeneratedOutputs();
      try {
        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(`${API_BASE}/api/source/upload`, { method: "POST", body: formData });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data?.error || "Failed to store uploaded file");
        }
        const nextFileId = String(data?.fileId || "");
        const nextFileName = String(data?.fileName || file.name);
        setStoredFileId(nextFileId);
        setStoredFileName(nextFileName);
        persistSourceSession("file", nextFileName, "", nextFileId, nextFileName);
      } catch (error) {
        console.error(error);
        toast.error(getReadableErrorMessage(error, "Failed to store uploaded file"));
        setStoredFileId("");
        setStoredFileName("");
      }
      return;
    }
    if (!hasText) {
      setInputMode("");
    }
  };


  const generateStudySetFromSource = async (source, navigateTo = "/study-set") => {
    const formData = new FormData();
    if (source?.mode === "file" && source?.fileId) {
      formData.append("fileId", source.fileId);
    } else if (source?.mode === "file" && source?.file instanceof File) {
      formData.append("file", source.file);
    } else if (source?.mode === "text") {
      formData.append("text", source.text || "");
    } else if (inputMode === "file" && storedFileId) {
      formData.append("fileId", storedFileId);
    } else if (inputMode === "file" && uploadFile instanceof File) {
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
      if (generatedMcqs.length < 10 || generatedFlashcards.length < 10) {
        throw new Error("Server did not return at least 10 MCQs and 10 flashcards");
      }

      setMcqs(generatedMcqs);
      setFlashcards(generatedFlashcards);
      setSummary(String(data?.summary || "").trim());
      setAudioUrl("");
      setMcqSetId(data?.mcqSetId || "");
      setMcqVerdicts({});
      setVerifyingAnswers({});
      toast.success("Study set generated: 10 MCQs + 10 Flashcards");
      const studySetPayload = {
        mcqs: generatedMcqs,
        flashcards: generatedFlashcards,
        summary: String(data?.summary || "").trim(),
        mcqSetId: data?.mcqSetId || "",
        sourceType: inputMode || (uploadFile || storedFileId ? "file" : "text"),
        sourcePreview: inputMode === "text" ? textValue.slice(0, 300) : storedFileName || uploadFile?.name || "",
        sourceText: inputMode === "text" ? textValue : "",
        sourceFileId: storedFileId,
        sourceFileName: storedFileName,
      };
      sessionStorage.setItem("educator_study_set", JSON.stringify(studySetPayload));
      navigate(navigateTo, { state: studySetPayload });
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to generate study set"));
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
    if (inputMode === "file" && storedFileId) {
      setLastSource({ mode: "file", fileId: storedFileId, label: storedFileName });
    } else if (inputMode === "file" && uploadFile) {
      setLastSource({ mode: "file", file: uploadFile, label: uploadFile.name });
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
      toast.error(getReadableErrorMessage(error, "Failed to verify answer"));
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
    const activeSource = getActiveSource();
    const sourceType =
      activeSource?.mode ||
      inputMode ||
      (uploadFile || storedFileId ? "file" : "text");
    const sourcePreview =
      activeSource?.label ||
      (activeSource?.mode === "text" ? activeSource.text?.slice(0, 300) : "") ||
      (inputMode === "text" ? textValue.slice(0, 300) : storedFileName || uploadFile?.name || "");
    const payload = {
      sourceType,
      sourcePreview,
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
      setSavingSession(true);
      await saveCurrentSession();
      toast.success("Saved. Ready for another source.");
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setAudioUrl("");
      setTextValue("");
      setUploadFile(null);
      setStoredFileId("");
      setStoredFileName("");
      setInputMode("");
      setSources([]);
      setRagQuestion("");
      setRagAnswer("");
      setVoiceQuestion("");
      setVoiceAnswer("");
      setVoiceAnswerAudioUrl("");
      setListening(false);
      setMcqGenerating(false);
      setFlashGenerating(false);
      setMcqReady(false);
      setFlashReady(false);
      setMcqPayload(null);
      setFlashPayload(null);
      setMcqs([]);
      setMcqSetId("");
      setMcqVerdicts({});
      setVerifyingAnswers({});
      setFlashcards([]);
      setSummary("");
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to save current session"));
    } finally {
      setSavingSession(false);
    }
  };

  const handleSaveSessionOnly = async () => {
    if (!hasSource && !hasResults) {
      toast.info("Add a source or generate MCQs/flashcards first");
      return;
    }
    try {
      setSavingSession(true);
      await saveCurrentSession();
      toast.success("Session saved to history");
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to save current session"));
    } finally {
      setSavingSession(false);
    }
  };

  const handleGenerateOtherSource = async () => {
    setAudioUrl("");
    setTextValue("");
    setUploadFile(null);
    setStoredFileId("");
    setStoredFileName("");
    setInputMode("");
    setSources([]);
    setRagQuestion("");
    setRagAnswer("");
    setVoiceQuestion("");
    setVoiceAnswer("");
    setVoiceAnswerAudioUrl("");
    setListening(false);
    setMcqGenerating(false);
    setFlashGenerating(false);
    setMcqReady(false);
    setFlashReady(false);
    setMcqPayload(null);
    setFlashPayload(null);
    setMcqs([]);
    setMcqSetId("");
    setMcqVerdicts({});
    setVerifyingAnswers({});
    setFlashcards([]);
    setSummary("");
  };

  const getActiveSource = () => {
    if (sources.length > 0) {
      return sources[0];
    }
    if (inputMode === "file" && storedFileId) {
      return { mode: "file", fileId: storedFileId, label: storedFileName };
    }
    if (inputMode === "file" && uploadFile) {
      return { mode: "file", file: uploadFile, label: uploadFile.name };
    }
    if (inputMode === "text" && textValue.trim()) {
      return { mode: "text", text: textValue.trim() };
    }
    return null;
  };

  const handleAskRag = async () => {
    if (!ragQuestion.trim()) {
      toast.info("Type a question for the AI guide.");
      return;
    }
    const formData = buildRagFormData(ragQuestion.trim(), "text");
    if (!formData) return;
    setRagLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/qa/source`, { method: "POST", body: formData });
      const rawText = await response.text();
      let data = null;
      try {
        data = rawText ? JSON.parse(rawText) : null;
      } catch (_error) {
        data = null;
      }
      if (!response.ok) {
        const message = data?.error || rawText || "Failed to answer question";
        throw new Error(message);
      }
      setRagAnswer(String(data?.answer || rawText || "").trim() || "No answer returned.");
    } catch (error) {
      console.error(error);
      const message = getReadableErrorMessage(error, "Failed to answer question");
      setRagAnswer(message);
      toast.error(message);
    } finally {
      setRagLoading(false);
    }
  };

  const buildRagFormData = (question, mode = "text") => {
    const activeSource = getActiveSource();
    if (!activeSource) {
      toast.info("Add a source before asking.");
      return null;
    }
    const formData = new FormData();
    formData.append("question", question);
    formData.append("mode", mode);
    if (activeSource.mode === "file" && activeSource.fileId) {
      formData.append("fileId", activeSource.fileId);
    } else if (activeSource.mode === "file" && activeSource.file instanceof File) {
      formData.append("file", activeSource.file);
    } else if (activeSource.mode === "text" && activeSource.text) {
      formData.append("text", activeSource.text);
    }
    return formData;
  };

  const askVoiceQuestion = async () => {
    const q = String(voiceQuestion || "").trim();
    if (!q) {
      toast.info("Ask a question first");
      return;
    }
    const formData = buildRagFormData(q, "voice");
    if (!formData) return;
    try {
      setVoiceLoading(true);
      const response = await fetch(`${API_BASE}/api/qa/source`, { method: "POST", body: formData });
      const rawText = await response.text();
      let data = null;
      try {
        data = rawText ? JSON.parse(rawText) : null;
      } catch (_error) {
        data = null;
      }
      if (!response.ok) {
        const message = data?.error || rawText || "Failed to answer question";
        throw new Error(message);
      }
      const answerText = String(data?.answer || rawText || "").trim() || "No answer returned.";
      setVoiceAnswer(answerText);
      const ttsResponse = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: answerText, language: ttsLanguage, translate: true }),
      });
      if (!ttsResponse.ok) {
        const err = await ttsResponse.json().catch(() => ({}));
        throw new Error(err?.error || "Failed to generate audio");
      }
      const blob = await ttsResponse.blob();
      const url = URL.createObjectURL(blob);
      if (voiceAnswerAudioUrl) {
        URL.revokeObjectURL(voiceAnswerAudioUrl);
      }
      setVoiceAnswerAudioUrl(url);
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to answer question"));
    } finally {
      setVoiceLoading(false);
    }
  };

  const handleToggleMic = () => {
    if (!recognizer) {
      toast.error("Speech Recognition is not supported in this browser");
      return;
    }
    if (listening) {
      recognizer.stop();
      setListening(false);
      return;
    }
    recognizer.lang = ttsLanguage === "hi" ? "hi-IN" : "en-US";
    try {
      recognizer.start();
      setListening(true);
    } catch (_error) {
      setListening(false);
    }
  };

  const openSourceModal = () => setSourceModalOpen(true);
  const closeSourceModal = () => setSourceModalOpen(false);

  const addSourceFromModal = () => {
    if (!canGenerate) {
      toast.info("Add text or upload a file first");
      return;
    }
    const nextSource =
      inputMode === "file" && (uploadFile || storedFileId)
        ? {
            id: `${Date.now()}-file`,
            type: "file",
            mode: "file",
            label: storedFileName || uploadFile?.name || "File source",
            file: uploadFile || null,
            fileId: storedFileId || "",
          }
        : {
            id: `${Date.now()}-text`,
            type: "text",
            mode: "text",
            label: textValue.trim().slice(0, 80) || "Text source",
            text: textValue.trim(),
          };
    setSources((prev) => [nextSource, ...prev]);
    setLastSource(
      nextSource.mode === "file"
        ? { mode: "file", file: nextSource.file, fileId: nextSource.fileId }
        : { mode: "text", text: nextSource.text }
    );
    setMcqReady(false);
    setFlashReady(false);
    setMcqPayload(null);
    setFlashPayload(null);
    resetGeneratedOutputs();
    persistSourceSession(
      nextSource.mode === "file" ? "file" : "text",
      nextSource.label,
      nextSource.mode === "text" ? nextSource.text : "",
      nextSource.mode === "file" ? nextSource.fileId : "",
      nextSource.mode === "file" ? nextSource.label : ""
    );
    closeSourceModal();
  };

  const buildStudySetPayload = (data) => {
    const sourceType = inputMode || (uploadFile || storedFileId ? "file" : "text");
    const sourcePreview =
      inputMode === "text" ? textValue.slice(0, 300) : storedFileName || uploadFile?.name || "";
    return {
      mcqs: Array.isArray(data?.mcqs) ? data.mcqs : [],
      flashcards: Array.isArray(data?.flashcards) ? data.flashcards : [],
      summary: String(data?.summary || "").trim(),
      mcqSetId: data?.mcqSetId || "",
      sourceType,
      sourcePreview,
      sourceText: inputMode === "text" ? textValue : "",
      sourceFileId: storedFileId,
      sourceFileName: storedFileName,
    };
  };

  useEffect(() => {
    const savedRaw = sessionStorage.getItem("educator_study_set");
    if (!savedRaw) return;
    if (mcqs.length || flashcards.length || summary || textValue || uploadFile || storedFileId) return;
    try {
      const saved = JSON.parse(savedRaw);
      const restoredMcqs = Array.isArray(saved?.mcqs) ? saved.mcqs : [];
      const restoredFlashcards = Array.isArray(saved?.flashcards) ? saved.flashcards : [];
      const restoredSummary = String(saved?.summary || "").trim();
      const restoredMcqSetId = String(saved?.mcqSetId || "").trim();
      if (restoredMcqs.length) setMcqs(restoredMcqs);
      if (restoredFlashcards.length) setFlashcards(restoredFlashcards);
      if (restoredSummary) setSummary(restoredSummary);
      if (restoredMcqSetId) setMcqSetId(restoredMcqSetId);
      if (restoredMcqs.length) {
        setMcqReady(true);
        setMcqPayload({
          mcqs: restoredMcqs,
          flashcards: [],
          summary: restoredSummary,
          mcqSetId: restoredMcqSetId,
          sourceType: saved?.sourceType || "",
          sourcePreview: saved?.sourcePreview || "",
        });
      }
      if (restoredFlashcards.length) {
        setFlashReady(true);
        setFlashPayload({
          mcqs: [],
          flashcards: restoredFlashcards,
          summary: restoredSummary,
          mcqSetId: restoredMcqSetId,
          sourceType: saved?.sourceType || "",
          sourcePreview: saved?.sourcePreview || "",
        });
      }
      if (saved?.sourceType === "text" && saved?.sourceText) {
        setTextValue(String(saved.sourceText));
        setInputMode("text");
        setLastSource({ mode: "text", text: String(saved.sourceText) });
        if (!sources.length) {
          setSources([
            {
              id: `${Date.now()}-text`,
              type: "text",
              mode: "text",
              label: String(saved.sourceText).slice(0, 80) || "Text source",
              text: String(saved.sourceText),
            },
          ]);
        }
      } else if (saved?.sourceType === "file" && saved?.sourceFileId) {
        setInputMode("file");
        setStoredFileId(String(saved.sourceFileId));
        setStoredFileName(String(saved.sourceFileName || saved.sourcePreview || "Uploaded file"));
        setLastSource({
          mode: "file",
          fileId: String(saved.sourceFileId),
          label: String(saved.sourceFileName || saved.sourcePreview || "Uploaded file"),
        });
        if (!sources.length) {
          setSources([
            {
              id: `${Date.now()}-file`,
              type: "file",
              mode: "file",
              label: String(saved.sourceFileName || saved.sourcePreview || "Uploaded file"),
              file: null,
              fileId: String(saved.sourceFileId),
            },
          ]);
        }
      }
    } catch (_error) {
      // ignore corrupt session
    }
  }, [mcqs.length, flashcards.length, summary, textValue, uploadFile, storedFileId, sources.length]);

  const handleGenerateMcqs = async () => {
    if (!canGenerate) {
      toast.info("Enter text or upload a file first");
      return;
    }
    try {
      setMcqGenerating(true);
      const formData = new FormData();
      const activeSource = getActiveSource();
      if (activeSource?.mode === "file" && activeSource.fileId) {
        formData.append("fileId", activeSource.fileId);
      } else if (activeSource?.mode === "file" && activeSource.file instanceof File) {
        formData.append("file", activeSource.file);
      } else if (activeSource?.mode === "text" && activeSource.text) {
        formData.append("text", activeSource.text);
      } else if (inputMode === "file" && storedFileId) {
        formData.append("fileId", storedFileId);
      } else if (inputMode === "file" && uploadFile instanceof File) {
        formData.append("file", uploadFile);
      } else {
        formData.append("text", textValue);
      }
      const response = await fetch(`${API_BASE}/api/generate/mcqs`, { method: "POST", body: formData });
      const rawText = await response.text();
      let data = {};
      try {
        data = rawText ? JSON.parse(rawText) : {};
      } catch (_error) {
        data = {};
      }
      if (!response.ok) {
        throw new Error(data?.error || rawText || "Failed to generate MCQs");
      }
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
      const mcqItems = normalizeArray(data?.mcqs);
      if (mcqItems.length === 0) {
        throw new Error("Server returned no MCQs");
      }
      const payload = buildStudySetPayload({
        mcqs: mcqItems,
        flashcards,
        summary,
        mcqSetId: data?.mcqSetId || mcqSetId || "",
      });
      sessionStorage.setItem("educator_study_set", JSON.stringify(payload));
      setMcqPayload(payload);
      setMcqReady(true);
      toast.success("MCQs generated. Click View to open.");
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to generate MCQs"));
    } finally {
      setMcqGenerating(false);
    }
  };

  const handleGenerateFlashcards = async () => {
    if (!canGenerate) {
      toast.info("Enter text or upload a file first");
      return;
    }
    try {
      setFlashGenerating(true);
      const formData = new FormData();
      const activeSource = getActiveSource();
      if (activeSource?.mode === "file" && activeSource.fileId) {
        formData.append("fileId", activeSource.fileId);
      } else if (activeSource?.mode === "file" && activeSource.file instanceof File) {
        formData.append("file", activeSource.file);
      } else if (activeSource?.mode === "text" && activeSource.text) {
        formData.append("text", activeSource.text);
      } else if (inputMode === "file" && storedFileId) {
        formData.append("fileId", storedFileId);
      } else if (inputMode === "file" && uploadFile instanceof File) {
        formData.append("file", uploadFile);
      } else {
        formData.append("text", textValue);
      }
      const response = await fetch(`${API_BASE}/api/generate/flashcards`, { method: "POST", body: formData });
      const rawText = await response.text();
      let data = {};
      try {
        data = rawText ? JSON.parse(rawText) : {};
      } catch (_error) {
        data = {};
      }
      if (!response.ok) {
        throw new Error(data?.error || rawText || "Failed to generate flashcards");
      }
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
      const flashItems = normalizeArray(data?.flashcards);
      if (flashItems.length === 0) {
        throw new Error("Server returned no flashcards");
      }
      const payload = buildStudySetPayload({
        mcqs,
        flashcards: flashItems,
        summary,
        mcqSetId,
      });
      sessionStorage.setItem("educator_study_set", JSON.stringify(payload));
      setFlashPayload(payload);
      setFlashReady(true);
      toast.success("Flashcards generated. Click View to open.");
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to generate flashcards"));
    } finally {
      setFlashGenerating(false);
    }
  };

  const handleViewMcqs = () => {
    if (!mcqPayload) return;
    navigate("/mcqs", { state: mcqPayload });
  };

  const handleViewFlashcards = () => {
    if (!flashPayload) return;
    navigate("/flashcards", { state: flashPayload });
  };

  const handleViewSummary = () => {
    if (!hasSummary) return;
    const payload = buildStudySetPayload({
      mcqs,
      flashcards,
      summary,
      mcqSetId,
    });
    sessionStorage.setItem("educator_study_set", JSON.stringify(payload));
    navigate("/summary", { state: payload });
  };

  const handleGenerateSummary = async () => {
    if (hasSummary) {
      handleViewSummary();
      return;
    }
    if (!canGenerate) {
      toast.info("Enter text or upload a file first");
      return;
    }
    try {
      setSummaryGenerating(true);
      const formData = new FormData();
      const activeSource = getActiveSource();
      if (activeSource?.mode === "file" && activeSource.fileId) {
        formData.append("fileId", activeSource.fileId);
      } else if (activeSource?.mode === "file" && activeSource.file instanceof File) {
        formData.append("file", activeSource.file);
      } else if (activeSource?.mode === "text" && activeSource.text) {
        formData.append("text", activeSource.text);
      } else if (inputMode === "file" && storedFileId) {
        formData.append("fileId", storedFileId);
      } else if (inputMode === "file" && uploadFile instanceof File) {
        formData.append("file", uploadFile);
      } else {
        formData.append("text", textValue);
      }
      const response = await fetch(`${API_BASE}/api/generate/summary`, { method: "POST", body: formData });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Failed to generate summary");
      }
      const nextSummary = String(data?.summary || "").trim();
      setSummary(nextSummary);
      const payload = buildStudySetPayload({
        mcqs,
        flashcards,
        summary: nextSummary,
        mcqSetId,
      });
      sessionStorage.setItem("educator_study_set", JSON.stringify(payload));
      toast.success("Summary generated");
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to generate summary"));
    } finally {
      setSummaryGenerating(false);
    }
  };

  const handleRemoveSource = (id) => {
    setSources((prev) => {
      const next = prev.filter((item) => item.id !== id);
      if (next.length === 0) {
        resetGeneratedOutputs();
        setTextValue("");
        setUploadFile(null);
        setStoredFileId("");
        setStoredFileName("");
        setInputMode("");
        setRagQuestion("");
        setRagAnswer("");
        setVoiceQuestion("");
        setVoiceAnswer("");
        setVoiceAnswerAudioUrl("");
        setListening(false);
        setLastSource(null);
        sessionStorage.removeItem("educator_study_set");
      }
      return next;
    });
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
      toast.error(getReadableErrorMessage(error, "Failed to generate audio"));
      return "";
    } finally {
      setAudioLoading(false);
    }
  };

  const getExportFilename = (response, format) => {
    const fallback = `study_set.${format === "quiz" ? "quiz.txt" : format}`;
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/i);
    return match?.[1] || fallback;
  };

  const handleExport = async (format) => {
    if (!hasResults) {
      toast.info("Generate study content first");
      return;
    }
    try {
      setExportingFormat(format);
      const response = await fetch(`${API_BASE}/api/export/study-set/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "educator_study_set",
          mcqs,
          flashcards,
          summary,
        }),
      });

      if (!response.ok) {
        let message = "Export failed";
        try {
          const data = await response.json();
          message = data?.error || message;
        } catch (_error) {
          const text = await response.text();
          if (text) {
            message = text;
          }
        }
        throw new Error(message);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const filename = getExportFilename(response, format);
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
      toast.error(getReadableErrorMessage(error, "Export failed"));
    } finally {
      setExportingFormat("");
    }
  };

  return (
    <main className="upload-page">
      <div className="home-bots" aria-hidden="true">
        <div className="boat-group">
          <img src="/blue.png" alt="" className="bot boat boat-blue" />
        </div>
      </div>
      <section className="upload-card upload-layout notebook-shell">
        <header className="upload-header">
          <button type="button" className="history-btn" onClick={() => navigate("/history")}>
            History
          </button>
          <h1>{displayName}, Welcome!! Here is the EduCator workspace</h1>
        </header>

        <div className="notebook-grid">
          <section className="notebook-card notebook-sources">
            <div className="card-header">
              <h2 className="card-title">Sources</h2>
            </div>
            <p className="card-subtitle">Add text, PDF, or docs to build a knowledge base.</p>
            <div className="notebook-card-body">
              <div className="sources-body">
                <div className="sources-empty">
                  <p>Click "Add source" to upload text or a file.</p>
                  <button type="button" className="add-source-btn" onClick={openSourceModal}>
                    + Add source
                  </button>
                </div>
                {sources.length > 0 && (
                  <ul className="sources-list">
                    {sources.map((item) => (
                      <li key={item.id} className="sources-item">
                        <span className="sources-type">{item.type === "file" ? "File" : "Text"}</span>
                        <span className="sources-label">{item.label}</span>
                        <button type="button" className="source-remove-btn" onClick={() => handleRemoveSource(item.id)}>
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </section>

          <section className="notebook-card notebook-chat">
            <div className="card-header">
              <h2 className="card-title">AI Guide</h2>
            </div>
            <p className="card-subtitle">Ask questions grounded in your uploaded sources.</p>
            <div className="notebook-card-body">
              {aiGuideMode === "voice" ? (
                <VoiceQASection
                  question={voiceQuestion}
                  onQuestionChange={setVoiceQuestion}
                  onAsk={askVoiceQuestion}
                  answer={voiceAnswer}
                  loading={voiceLoading}
                  listening={listening}
                  onToggleMic={handleToggleMic}
                  audioUrl={voiceAnswerAudioUrl}
                />
              ) : (
                <>
                  <div className="rag-input">
                    <input
                      type="text"
                      value={ragQuestion}
                      onChange={(event) => setRagQuestion(event.target.value)}
                      placeholder="Ask anything about your sources..."
                      disabled={ragLoading}
                    />
                    <button type="button" onClick={handleAskRag} disabled={ragLoading}>
                      {ragLoading ? "Asking..." : "Ask"}
                    </button>
                  </div>
                  <div className="rag-answer">
                    {ragAnswer
                      ? ragAnswer
                      : ragLoading
                      ? "Thinking..."
                      : "Upload a source and ask a question to get a guided response."}
                  </div>
                </>
              )}
            </div>
          </section>

          <section className="notebook-card notebook-tools">
            <div className="card-header">
              <h2 className="card-title">Tools</h2>
            </div>
            <p className="card-subtitle">Summaries, MCQs, and flashcards for now.</p>
            <div className="notebook-card-body tools-stack">
              <div className="tool-actions">
                <button
                  type="button"
                  className="tool-action-card"
                  onClick={() => setAiGuideMode((prev) => (prev === "voice" ? "text" : "voice"))}
                >
                  <span className="tool-action-title">
                    {aiGuideMode === "voice" ? "AI Text Assistant" : "AI Voice Assistant"}
                  </span>
                  <span className="tool-action-subtitle">
                    {aiGuideMode === "voice" ? "Switch to text-based guide" : "Ask by voice and hear replies"}
                  </span>
                </button>
                <button
                  type="button"
                  className={`tool-action-card ${mcqReady ? "tool-action-ready" : ""}`}
                  onClick={mcqReady ? handleViewMcqs : handleGenerateMcqs}
                  disabled={
                    mcqReady
                      ? !mcqPayload
                      : !canGenerate || loadingStudySet || mcqGenerating || flashGenerating
                  }
                >
                  <span className="tool-action-title">
                    {mcqReady ? "MCQs Ready" : mcqGenerating ? "Generating MCQs..." : "Generate MCQs"}
                  </span>
                  <span className="tool-action-subtitle">
                    {mcqReady ? "Click to open your generated questions" : "Auto-create questions from sources"}
                  </span>
                  {!mcqReady && mcqGenerating && <span className="tool-action-spinner" aria-hidden="true" />}
                </button>
                <button
                  type="button"
                  className={`tool-action-card ${flashReady ? "tool-action-ready" : ""}`}
                  onClick={flashReady ? handleViewFlashcards : handleGenerateFlashcards}
                  disabled={
                    flashReady ? !flashPayload : !canGenerate || loadingStudySet || flashGenerating || mcqGenerating
                  }
                >
                  <span className="tool-action-title">
                    {flashReady ? "Flashcards Ready" : flashGenerating ? "Generating Flashcards..." : "Generate Flashcards"}
                  </span>
                  <span className="tool-action-subtitle">
                    {flashReady ? "Click to open your flashcards" : "Create quick recall cards"}
                  </span>
                  {flashGenerating && <span className="tool-action-spinner" aria-hidden="true" />}
                </button>
                <button
                  type="button"
                  className={`tool-action-card ${hasSummary ? "tool-action-ready" : ""}`}
                  onClick={handleGenerateSummary}
                  disabled={summaryGenerating || (!hasSummary && !canGenerate)}
                >
                  <span className="tool-action-title">
                    {hasSummary ? "Summary Ready" : summaryGenerating ? "Generating Summary..." : "Summary"}
                  </span>
                  <span className="tool-action-subtitle">
                    {hasSummary ? "Click to open your generated summary" : "Generate a summary from your source"}
                  </span>
                  {summaryGenerating && <span className="tool-action-spinner" aria-hidden="true" />}
                </button>
              </div>

            </div>
          </section>
        </div>

        <div className="workspace-actions">
          <div className="workspace-primary-actions">
            <button
              type="button"
              className="save-session-btn primary-action-btn"
              onClick={handleSaveSessionOnly}
              disabled={savingSession || !hasSource}
            >
              {savingSession ? "Saving..." : "Save Session"}
            </button>
            <button
              type="button"
              className="save-session-btn primary-action-btn"
              onClick={handleGenerateOtherSource}
            >
              Generate New Source Content
            </button>
          </div>
        </div>
      </section>

      {sourceModalOpen && (
        <div className="modal-overlay" role="presentation" onClick={closeSourceModal}>
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-source-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button type="button" className="modal-close" onClick={closeSourceModal} aria-label="Close">
              x
            </button>
            <header className="modal-header">
              <h2 id="add-source-title">Add a Source</h2>
              <p>Upload text or a file to build your knowledge base.</p>
            </header>
            <div className="modal-body">
              <InputSection
                textValue={textValue}
                onTextChange={handleTextChange}
                uploadFile={uploadFile}
                uploadFileName={storedFileName}
                onFileChange={handleFileChange}
                canUseText={canUseText}
                canUseFile={canUseFile}
              />
              <div className="modal-actions">
                <button type="button" className="ghost-btn" onClick={closeSourceModal}>
                  Cancel
                </button>
                <button type="button" onClick={addSourceFromModal} disabled={!canGenerate}>
                  Add Source
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default UploadPage;


