import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import { callClaude } from "../../utils/callClaude";
import DifficultySelect, { normalizeDifficulty } from "./DifficultySelect";
import ExportSection from "./ExportSection";
import MatchThePairSection from "./MatchThePairSection";

function MatchThePairPage() {
  const location = useLocation();
  const navigate = useNavigate();
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
  const initialSets = Array.isArray(routeState?.matchThePair?.sets) ? routeState.matchThePair.sets : [];
  const [sets, setSets] = useState(initialSets);
  const [exportingFormat, setExportingFormat] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const sourceText = String(routeState?.sourceText || "").trim();
  const sourceFileId = String(routeState?.sourceFileId || "").trim();
  const difficultySaved =
    routeState?.difficultyByMode && typeof routeState.difficultyByMode === "object" ? routeState.difficultyByMode : {};
  const [difficulty, setDifficulty] = useState(normalizeDifficulty(difficultySaved.match_the_pair || "medium"));

  const updateStudySetStorage = (partial) => {
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
      const data = await callClaude("matchpair", formData, { difficulty: nextDifficulty, count: 25 });
      const nextSets = Array.isArray(data?.matchThePair?.sets) ? data.matchThePair.sets : [];
      if (nextSets.length === 0) {
        throw new Error("Server returned no match-the-pair sets");
      }
      setSets(nextSets);
      const nextDifficultyByMode = {
        ...(typeof routeState?.difficultyByMode === "object" ? routeState.difficultyByMode : {}),
        match_the_pair: normalizeDifficulty(nextDifficulty),
      };
      updateStudySetStorage({ matchThePair: { sets: nextSets, setCount: 5, pairsPerSet: 5 }, difficultyByMode: nextDifficultyByMode });
      toast.success("Match-the-pair regenerated");
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
          title: "match_the_pair",
          matchThePair: { sets, setCount: sets.length, pairsPerSet: 5 },
          mcqs: [],
          flashcards: [],
          fillBlanks: [],
          trueFalse: [],
          summary: "",
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.error || "Export failed");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const fallback = `match_the_pair.${format === "quiz" ? "txt" : format}`;
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

  if (sets.length === 0) {
    return (
      <main className="upload-page">
        <section className="upload-card upload-layout">
          <header className="upload-header">
            <h1>No Match-the-Pair Found</h1>
            <p>Generate Match-the-Pair first from Upload page.</p>
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
          <h1>Match the Pair</h1>
          <p>Practice associations by matching terms, concepts, and examples.</p>
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

        <MatchThePairSection sets={sets} />
        <ExportSection
          hasResults={sets.length > 0}
          exportingFormat={exportingFormat}
          onExport={handleExport}
          mode="match_the_pair"
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

export default MatchThePairPage;

