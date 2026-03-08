import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import SummarySection from "./SummarySection";

function SummaryPage() {
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
  const [summary] = useState(String(routeState?.summary || "").trim());
  const [audioUrl, setAudioUrl] = useState("");
  const [audioLoading, setAudioLoading] = useState(false);
  const [ttsLanguage, setTtsLanguage] = useState("en");

  const handleGoBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/upload");
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
      toast.error(error?.message || "Failed to generate audio");
      return "";
    } finally {
      setAudioLoading(false);
    }
  };

  if (!summary) {
    return (
      <main className="upload-page">
        <section className="upload-card upload-layout">
          <header className="upload-header">
            <h1>No Summary Found</h1>
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
          <h1>Study Summary</h1>
          <p>Your generated summary in one place.</p>
        </header>
        <div style={{ textAlign: "center", marginBottom: "0.8rem" }}>
          <button type="button" onClick={handleGoBack}>
            Back
          </button>
        </div>
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
      </section>
    </main>
  );
}

export default SummaryPage;
