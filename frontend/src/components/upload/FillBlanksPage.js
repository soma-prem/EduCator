import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import { auth } from "../../firebase";
import DifficultySelect, { normalizeDifficulty } from "./DifficultySelect";
import ExportSection from "./ExportSection";
import KnowledgeGapSection from "./KnowledgeGapSection";
import FillBlanksSection from "./FillBlanksSection";
import usePremium from "../../premium/usePremium";
import UpgradeNotice from "../premium/UpgradeNotice";

function FillBlanksPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const premium = usePremium();
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
  const [fillBlanks, setFillBlanks] = useState(Array.isArray(routeState?.fillBlanks) ? routeState.fillBlanks : []);
  const [exportingFormat, setExportingFormat] = useState("");
  const [answers, setAnswers] = useState({});
  const [checkedMap, setCheckedMap] = useState({});
  const [knowledgeGapLoading, setKnowledgeGapLoading] = useState(false);
  const [knowledgeGapResult, setKnowledgeGapResult] = useState(null);
  const [regenerating, setRegenerating] = useState(false);
  const sourceText = String(routeState?.sourceText || "").trim();
  const sourceFileId = String(routeState?.sourceFileId || "").trim();
  const difficultySaved =
    routeState?.difficultyByMode && typeof routeState.difficultyByMode === "object" ? routeState.difficultyByMode : {};
  const [difficulty, setDifficulty] = useState(normalizeDifficulty(difficultySaved.fill_blanks || "medium"));

  if (!premium.canUse("fill_blanks")) {
    return (
      <main className="upload-page">
        <section className="upload-card upload-layout notebook-shell">
          <header className="upload-header">
            <h1>Fill in the Blanks</h1>
            <p>This is a Premium feature.</p>
          </header>
          <UpgradeNotice title="Fill in the Blanks" message="Upgrade to Silver (or higher) to unlock this feature." />
          <div style={{ textAlign: "center", marginTop: "1rem" }}>
            <button type="button" onClick={() => navigate("/uplod")}>
              Back
            </button>
          </div>
        </section>
      </main>
    );
  }

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

  const buildSourceFormData = (nextDifficulty) => {
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
        formData.append("difficulty", normalizeDifficulty(nextDifficulty));
        return formData;
      }
    }
    if (sourceFileId) {
      formData.append("fileId", sourceFileId);
    } else if (sourceText) {
      formData.append("text", sourceText);
    } else if (String(routeState?.sourceFileId || "").trim()) {
      formData.append("fileId", String(routeState.sourceFileId).trim());
    } else if (String(routeState?.sourceText || "").trim()) {
      formData.append("text", String(routeState.sourceText).trim());
    } else {
      return null;
    }
    formData.append("difficulty", normalizeDifficulty(nextDifficulty));
    return formData;
  };

  const regenerate = async (nextDifficulty) => {
    const formData = buildSourceFormData(nextDifficulty);
    if (!formData) {
      toast.error("Source missing. Go back to Upload and generate again.");
      return;
    }
    setRegenerating(true);
    try {
      formData.append("tool", "fill_blanks");
      formData.append("count", "12");
      const token = auth.currentUser ? await auth.currentUser.getIdToken() : "";
      const response = await fetch(`${API_BASE}/api/tools/generate`, {
        method: "POST",
        body: formData,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Failed to regenerate fill-in-the-blanks");
      }
      const items = Array.isArray(data?.fillBlanks) ? data.fillBlanks : [];
      if (items.length === 0) {
        throw new Error("Server returned no fill-in-the-blanks questions");
      }
      setFillBlanks(items);
      setAnswers({});
      setCheckedMap({});
      setKnowledgeGapResult(null);
      const nextDifficultyByMode = {
        ...(typeof routeState?.difficultyByMode === "object" ? routeState.difficultyByMode : {}),
        fill_blanks: normalizeDifficulty(nextDifficulty),
      };
      updateSessionStorage({ fillBlanks: items, difficultyByMode: nextDifficultyByMode });
      toast.success("Fill-in-the-blanks regenerated");
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
          title: "fill_blanks",
          fillBlanks,
          mcqs: [],
          flashcards: [],
          summary: "",
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.error || "Export failed");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const fallback = `fill_blanks.${format === "quiz" ? "txt" : format}`;
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

  const handleAnalyzeKnowledgeGaps = async () => {
    try {
      setKnowledgeGapLoading(true);
      const submitted = {};
      Object.keys(checkedMap).forEach((key) => {
        if (!checkedMap[key]) return;
        const value = answers[key];
        if (typeof value === "string" && value.trim()) {
          submitted[key] = value;
        }
      });
      const token = auth.currentUser ? await auth.currentUser.getIdToken() : "";
      const response = await fetch(`${API_BASE}/api/recommend/knowledge-gaps/content`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          mode: "fill_blanks",
          items: fillBlanks,
          attempts: submitted,
          threshold: 0.6,
          language: "en",
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

  if (fillBlanks.length === 0) {
    return (
      <main className="upload-page">
        <section className="upload-card upload-layout">
          <header className="upload-header">
            <h1>No Fill-in-the-Blanks Found</h1>
            <p>Generate fill-in-the-blanks first from Upload page.</p>
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
          <h1>Fill in the Blanks</h1>
          <p>Practice key concepts with quick blanks.</p>
          <DifficultySelect
            value={difficulty}
            onChange={(value) => {
              const next = normalizeDifficulty(value);
              setDifficulty(next);
              regenerate(next);
            }}
            disabled={regenerating}
          />
        </header>
        <ExportSection
          hasResults={fillBlanks.length > 0}
          exportingFormat={exportingFormat}
          onExport={handleExport}
          mode="fill_blanks"
        />
        <FillBlanksSection
          items={fillBlanks}
          answers={answers}
          checkedMap={checkedMap}
          onAnswer={(index, value) => setAnswers((prev) => ({ ...prev, [index]: value }))}
          onCheck={(index) => setCheckedMap((prev) => ({ ...prev, [index]: true }))}
        />
        <KnowledgeGapSection
          result={knowledgeGapResult}
          loading={knowledgeGapLoading}
          onAnalyze={handleAnalyzeKnowledgeGaps}
          locked={!premium.canUse("knowledge_gap")}
          onUpgrade={() => navigate("/premium")}
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

export default FillBlanksPage;
