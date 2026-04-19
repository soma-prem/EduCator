import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import DifficultySelect, { normalizeDifficulty } from "./DifficultySelect";
import MatchThePairSection from "./MatchThePairSection";

function MatchThePairPage() {
  const location = useLocation();
  const navigate = useNavigate();
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
  const initialSets = Array.isArray(routeState?.matchThePair?.sets) ? routeState.matchThePair.sets : [];
  const [sets, setSets] = useState(initialSets);
  const [regenerating, setRegenerating] = useState(false);
  const sourceText = String(routeState?.sourceText || "").trim();
  const sourceFileId = String(routeState?.sourceFileId || "").trim();
  const difficultySaved =
    routeState?.difficultyByMode && typeof routeState.difficultyByMode === "object" ? routeState.difficultyByMode : {};
  const [difficulty, setDifficulty] = useState(normalizeDifficulty(difficultySaved.match_the_pair || "medium"));

  const updateSessionStorage = (partial) => {
    const savedRaw = sessionStorage.getItem("educator_study_set");
    let saved = {};
    if (savedRaw) {
      try {
        saved = JSON.parse(savedRaw) || {};
      } catch (_error) {
        saved = {};
      }
    }
    const next = { ...saved, ...partial };
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
      formData.append("tool", "match_the_pair");
      formData.append("count", "25");
      const response = await fetch(`${API_BASE}/api/tools/generate`, { method: "POST", body: formData });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Failed to regenerate match-the-pair");
      }
      const nextSets = Array.isArray(data?.matchThePair?.sets) ? data.matchThePair.sets : [];
      if (nextSets.length === 0) {
        throw new Error("Server returned no match-the-pair sets");
      }
      setSets(nextSets);
      const nextDifficultyByMode = {
        ...(typeof routeState?.difficultyByMode === "object" ? routeState.difficultyByMode : {}),
        match_the_pair: normalizeDifficulty(nextDifficulty),
      };
      updateSessionStorage({ matchThePair: { sets: nextSets, setCount: 5, pairsPerSet: 5 }, difficultyByMode: nextDifficultyByMode });
      toast.success("Match-the-pair regenerated");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "Failed to regenerate");
    } finally {
      setRegenerating(false);
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
      </section>
    </main>
  );
}

export default MatchThePairPage;

