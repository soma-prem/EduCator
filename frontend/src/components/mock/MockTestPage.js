import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import { callClaude } from "../../utils/callClaude";
import "./MockTestPage.css";
import usePremium from "../../premium/usePremium";
import UpgradeNotice from "../premium/UpgradeNotice";
import { auth } from "../../firebase";

function MockTestPage() {
  const navigate = useNavigate();
  const premium = usePremium();

  const [syllabusFile, setSyllabusFile] = useState(null);
  const [pastFile, setPastFile] = useState(null);
  const [totalQuestions, setTotalQuestions] = useState(20);
  const [durationMinutes, setDurationMinutes] = useState(60);

  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!generating) {
      setProgress(0);
      return;
    }
    setProgress(8);
    const id = setInterval(() => {
      setProgress((prev) => {
        const cap = 92;
        if (prev >= cap) return prev;
        const next = prev + Math.max(1, Math.round((cap - prev) * 0.12));
        return Math.min(cap, next);
      });
    }, 450);
    return () => clearInterval(id);
  }, [generating]);

  if (!premium.canUse("mock_exam")) {
    return (
      <main className="mock-builder-page">
        <section className="notebook-shell">
          <div className="notebook-grid notebook-grid-full">
            <section className="notebook-card">
              <div className="card-header">
                <h2 className="card-title">Mock Test</h2>
              </div>
              <p className="card-subtitle">This is a Premium feature.</p>
              <div className="notebook-card-body mock-builder-body">
                <UpgradeNotice title="Mock Exam" message="Upgrade to Platinum to unlock mock exams." />
                <div style={{ textAlign: "center", marginTop: "1rem" }}>
                  <button type="button" className="ghost-btn" onClick={() => navigate("/uplod")}> 
                    Back
                  </button>
                </div>
              </div>
            </section>
          </div>
        </section>
      </main>
    );
  }

  const getReadableErrorMessage = (error, fallbackMessage) => {
    const raw = String(error?.message || "").toLowerCase();
    if (raw.includes("failed to fetch") || raw.includes("networkerror") || raw.includes("load failed")) {
      return `Cannot reach backend at ${API_BASE}. Start backend server and verify CORS/API URL.`;
    }
    return error?.message || fallbackMessage;
  };

  const handleGenerate = async () => {
    const hasSyllabusFile = syllabusFile instanceof File;
    const hasPastFile = pastFile instanceof File;

    if (!hasSyllabusFile && !hasPastFile) {
      toast.info("Upload a syllabus or previous year papers file first.");
      return;
    }

    try {
      setGenerating(true);
      setProgress(10);

      const token = auth.currentUser ? await auth.currentUser.getIdToken() : "";
      const formData = new FormData();
      formData.append("totalQuestions", Number(totalQuestions) || 20);
      formData.append("durationMinutes", Number(durationMinutes) || 60);

      const primaryFile = hasSyllabusFile ? syllabusFile : pastFile;
      formData.append("file", primaryFile);
      formData.append("mode", "file");

      if (hasSyllabusFile && hasPastFile) {
        formData.append("pastFile", pastFile);
      }

      const data = await callClaude("mocktest", formData, { authToken: token });

      const nextMock = data?.mockExam || {};
      const normalizedMock = {
        ...nextMock,
        timing: {
          ...(nextMock?.timing || {}),
          totalMinutes: Number(nextMock?.timing?.totalMinutes || durationMinutes || 60),
        },
        requestedTotalQuestions: Number(totalQuestions) || 20,
        requestedDurationMinutes: Number(durationMinutes) || 60,
      };

      sessionStorage.setItem("educator_exam_mock", JSON.stringify(normalizedMock));
      toast.success("Mock exam ready");
      setProgress(100);
      navigate("/exam-mock", { state: { mockExam: normalizedMock } });
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to generate mock exam"));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <main className="mock-builder-page">
      <section className="notebook-shell">
        <div className="notebook-grid notebook-grid-full">
          <section className="notebook-card">
            <div className="card-header">
              <h2 className="card-title">Mock Test</h2>
            </div>

            <div className="notebook-card-body mock-builder-body">
              <div className="mock-exam-panel">
                <div className="mock-builder-grid">
                  <section className="mock-builder-card">
                    <div className="mock-card-head">
                      <h4>Upload sources</h4>
                      <p>Upload syllabus and/or previous year papers.</p>
                    </div>

                    <div className="mock-field-grid mock-field-grid-two">
                      <div className="field">
                        <span>Syllabus file</span>
                        <input
                          type="file"
                          accept=".pdf,.docx,.pptx,.txt"
                          onChange={(e) => setSyllabusFile(e.target.files?.[0] || null)}
                          disabled={generating}
                        />
                        {syllabusFile && <p className="file-hint">Using: {syllabusFile.name}</p>}
                      </div>

                      <div className="field">
                        <span>Previous year papers file</span>
                        <input
                          type="file"
                          accept=".pdf,.docx,.pptx,.txt"
                          onChange={(e) => setPastFile(e.target.files?.[0] || null)}
                          disabled={generating}
                        />
                        {pastFile && <p className="file-hint">Using: {pastFile.name}</p>}
                      </div>
                    </div>
                  </section>

                  <section className="mock-builder-card mock-builder-settings">
                    <div className="mock-card-head">
                      <h4>Exam settings</h4>
                      <p>Pick a length that matches your real test.</p>
                    </div>

                    <div className="mock-exam-controls">
                      <label>
                        <span>Total questions</span>
                        <input
                          type="number"
                          min="5"
                          max="100"
                          value={totalQuestions}
                          onChange={(e) => setTotalQuestions(e.target.value)}
                          disabled={generating}
                        />
                      </label>
                      <label>
                        <span>Duration (minutes)</span>
                        <input
                          type="number"
                          min="10"
                          max="240"
                          value={durationMinutes}
                          onChange={(e) => setDurationMinutes(e.target.value)}
                          disabled={generating}
                        />
                      </label>
                    </div>

                    <div className="mock-presets">
                      <button
                        type="button"
                        className="ghost-btn"
                        onClick={() => {
                          setTotalQuestions(20);
                          setDurationMinutes(60);
                        }}
                        disabled={generating}
                      >
                        20Q / 60m
                      </button>
                      <button
                        type="button"
                        className="ghost-btn"
                        onClick={() => {
                          setTotalQuestions(30);
                          setDurationMinutes(90);
                        }}
                        disabled={generating}
                      >
                        30Q / 90m
                      </button>
                      <button
                        type="button"
                        className="ghost-btn"
                        onClick={() => {
                          setTotalQuestions(50);
                          setDurationMinutes(120);
                        }}
                        disabled={generating}
                      >
                        50Q / 120m
                      </button>
                    </div>

                    <div className="mock-builder-actions">
                      <button type="button" className="ghost-btn" onClick={() => navigate("/uplod")} disabled={generating}>
                        Back to Upload
                      </button>
                      <button type="button" className="primary-action-btn" onClick={handleGenerate} disabled={generating}>
                        {generating ? "Generating..." : "Generate Mock Test"}
                      </button>
                    </div>

                    {generating ? (
                      <div className="mock-progress" aria-live="polite" aria-busy="true">
                        <div className="mock-progress-track">
                          <div className="mock-progress-bar" style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
                        </div>
                        <div className="mock-progress-meta">
                          <span>Generating exam…</span>
                          <span>{Math.min(100, Math.max(0, Math.round(progress)))}%</span>
                        </div>
                      </div>
                    ) : null}
                  </section>
                </div>
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

export default MockTestPage;
