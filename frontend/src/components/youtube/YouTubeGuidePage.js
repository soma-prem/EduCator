import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { API_BASE } from "../../config/api";
import "./YouTubeGuidePage.css";
import usePremium from "../../premium/usePremium";
import UpgradeNotice from "../premium/UpgradeNotice";
import { auth } from "../../firebase";

function YouTubeGuidePage() {
  const navigate = useNavigate();
  const premium = usePremium();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [videos, setVideos] = useState([]);
  const [selectedVideoId, setSelectedVideoId] = useState("");

  const savedStudySet = useMemo(() => {
    try {
      const raw = localStorage.getItem("educator_study_set") || sessionStorage.getItem("educator_study_set");
      return raw ? JSON.parse(raw) : null;
    } catch (_error) {
      return null;
    }
  }, []);

  const getReadableErrorMessage = (err, fallbackMessage) => {
    const raw = String(err?.message || "").toLowerCase();
    if (raw.includes("failed to fetch") || raw.includes("networkerror") || raw.includes("load failed")) {
      return `Cannot reach backend at ${API_BASE}. Start backend server and verify CORS/API URL.`;
    }
    return err?.message || fallbackMessage;
  };

  const buildFormData = () => {
    const formData = new FormData();
    formData.append("maxResults", "12");

    const snapshot = savedStudySet;
    const sources = Array.isArray(snapshot?.sources) ? snapshot.sources : [];

    if (sources.length > 0) {
      for (const item of sources) {
        if (item?.mode === "text" && item?.text) {
          formData.append("text", String(item.text));
        }
        if (item?.mode === "file" && item?.fileId) {
          formData.append("fileId", String(item.fileId));
        }
      }
      return formData;
    }

    const sourceText = String(snapshot?.sourceText || "").trim();
    const sourceFileId = String(snapshot?.sourceFileId || "").trim();
    if (sourceText) {
      formData.append("text", sourceText);
      return formData;
    }
    if (sourceFileId) {
      formData.append("fileId", sourceFileId);
      return formData;
    }

    return null;
  };

  const fetchRecommendations = async () => {
    const formData = buildFormData();
    if (!formData) {
      toast.info("Add a source in Upload first.");
      navigate("/uplod");
      return;
    }

    setLoading(true);
    setError("");
    try {
      // Note: This endpoint is premium-gated on backend.
      const token = auth.currentUser ? await auth.currentUser.getIdToken() : "";
      const response = await fetch(`${API_BASE}/api/youtube/recommend`, {
        method: "POST",
        body: formData,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const raw = await response.text();
      let data = null;
      try {
        data = raw ? JSON.parse(raw) : null;
      } catch (_error) {
        data = null;
      }
      if (!response.ok) {
        throw new Error(data?.error || raw || "Failed to load YouTube recommendations");
      }

      const nextVideos = Array.isArray(data?.videos) ? data.videos : [];
      setVideos(nextVideos);
      setSelectedVideoId(nextVideos[0]?.videoId ? String(nextVideos[0].videoId) : "");

      if (nextVideos.length === 0) {
        setError("No videos found for your source. Try adding more content or a different source.");
      }
    } catch (err) {
      console.error(err);
      setError(getReadableErrorMessage(err, "Failed to load YouTube recommendations"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!premium.canUse("youtube_guide")) return;
    fetchRecommendations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [premium]);

  if (!premium.canUse("youtube_guide")) {
    return (
      <main className="youtube-guide-page">
        <section className="notebook-shell">
          <div className="notebook-grid notebook-grid-full">
            <section className="notebook-card youtube-guide-card">
              <div className="card-header">
                <h2 className="card-title">YouTube Guide</h2>
                <div className="card-actions">
                  <button type="button" className="ghost-btn" onClick={() => navigate("/uplod")}>
                    Back
                  </button>
                </div>
              </div>
              <p className="card-subtitle">This is a Premium feature.</p>
              <div className="notebook-card-body youtube-guide-body">
                <UpgradeNotice title="YouTube Guide" message="Upgrade to Platinum to unlock YouTube recommendations." />
              </div>
            </section>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="youtube-guide-page">
      <section className="notebook-shell">
        <div className="notebook-grid notebook-grid-full">
          <section className="notebook-card youtube-guide-card">
            <div className="card-header">
              <h2 className="card-title">YouTube Guide</h2>
              <div className="card-actions">
                <button type="button" className="ghost-btn" onClick={() => navigate("/uplod")}>
                  Back
                </button>
                <button type="button" className="primary-action-btn" onClick={fetchRecommendations} disabled={loading}>
                  {loading ? "Refreshing..." : "Refresh"}
                </button>
              </div>
            </div>

            <div className="notebook-card-body youtube-guide-body">
              {loading && <div className="rag-answer">Finding the best videos...</div>}
              {!loading && error ? <div className="rag-answer">{error}</div> : null}

              {!loading && !error && (
                <>
                  <div className="youtube-rec-grid" role="list">
                    {videos.map((video) => (
                      <button
                        key={video.videoId}
                        type="button"
                        className={`youtube-rec-card ${selectedVideoId === video.videoId ? "is-selected" : ""}`}
                        onClick={() => setSelectedVideoId(video.videoId ? String(video.videoId) : "")}
                        role="listitem"
                      >
                        <img
                          className="youtube-rec-thumb"
                          src={video.thumbnailUrl}
                          alt={video.title || "Video thumbnail"}
                          loading="lazy"
                        />
                        <div className="youtube-rec-meta">
                          <div className="youtube-rec-card-title">{video.title}</div>
                          <div className="youtube-rec-channel">{video.channelTitle}</div>
                        </div>
                      </button>
                    ))}
                  </div>

                  {selectedVideoId ? (
                    <div className="youtube-player-shell" aria-label="Selected YouTube video player">
                      <div className="youtube-player-frame">
                        <iframe
                          title="YouTube video player"
                          src={`https://www.youtube.com/embed/${encodeURIComponent(
                            selectedVideoId
                          )}?controls=1&rel=0&modestbranding=1&playsinline=1&enablejsapi=1`}
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                          allowFullScreen
                        />
                      </div>

                      <div className="youtube-player-actions">
                        <button
                          type="button"
                          className="ghost-btn"
                          onClick={() => window.open(`https://www.youtube.com/watch?v=${encodeURIComponent(selectedVideoId)}`, "_blank", "noopener,noreferrer")}
                        >
                          Open on YouTube
                        </button>
                        <div className="youtube-player-hint">Use the player settings (gear) for playback speed.</div>
                      </div>
                    </div>
                  ) : null}

                  {videos.length === 0 ? (
                    <div className="youtube-guide-empty-list">No videos match your search.</div>
                  ) : null}
                </>
              )}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

export default YouTubeGuidePage;
