import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./App.css";
import { auth } from "./firebase";
import Login from "./components/auth/Login";
import UploadPage from "./components/upload/UploadPage";
import StudySetPage from "./components/upload/StudySetPage";
import McqPage from "./components/upload/McqPage";
import FlashcardPage from "./components/upload/FlashcardPage";
import HistoryPage from "./components/upload/HistoryPage";
import AnalyticsPage from "./components/upload/AnalyticsPage";
import SummaryPage from "./components/upload/SummaryPage";
import FillBlanksPage from "./components/upload/FillBlanksPage";
import TrueFalsePage from "./components/upload/TrueFalsePage";
<<<<<<< HEAD
import ExamMockPage from "./components/upload/ExamMockPage";
import MockTestPage from "./components/mock/MockTestPage";
import YouTubeGuidePage from "./components/youtube/YouTubeGuidePage";
import PremiumPage from "./components/premium/PremiumPage";
import usePremium from "./premium/usePremium";
import { hasFeature, requiredPlanForFeature } from "./premium/plans";
import CrownIcon from "./components/premium/CrownIcon";
=======
import MatchThePairPage from "./components/upload/MatchThePairPage";
>>>>>>> 5880e86 (Project ready)

function App() {
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const premium = usePremium();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setAuthReady(true);
    });

    return () => unsubscribe();
  }, []);

  const openUpload = () => {
    if (!user) {
      toast.info("Login first");
      navigate("/login", { state: { from: "/uplod" } });
      return;
    }

    navigate("/uplod");
  };

  const openMockTest = async () => {
    if (!user) {
      toast.info("Login first");
      navigate("/login", { state: { from: "/mock-test" } });
      return;
    }

    const nowSec = Math.floor(Date.now() / 1000);
    let latest = null;
    try {
      latest = await premium.refresh();
    } catch (_error) {
      latest = null;
    }

    const plan = String(latest?.plan ?? premium.plan ?? "free").trim().toLowerCase();
    const active = Boolean(latest?.active ?? premium.active);
    const expiresAtEpoch = Number(latest?.expiresAtEpoch ?? premium.expiresAtEpoch ?? 0);
    const allowed = active && expiresAtEpoch > nowSec && hasFeature(plan, "mock_exam");

    if (!allowed) {
      toast.info(`Upgrade to ${requiredPlanForFeature("mock_exam")} to unlock Mock Exam.`);
      navigate("/premium");
      return;
    }
    navigate("/mock-test");
  };

  const handleUploadNavClick = (event) => {
    event.preventDefault();
    openUpload();
  };

  const handleMockTestNavClick = (event) => {
    event.preventDefault();
    openMockTest().catch(() => {});
  };

  const handleLogout = async () => {
    await signOut(auth);
    toast.success("Logged out");
    if (location.pathname === "/uplod") {
      navigate("/");
    }
  };

  if (!authReady) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <Link className="brand" to="/">
          EduCator
        </Link>
        <div className="rain-zone" aria-hidden="true">
          <span className="drop d1" />
          <span className="drop d2" />
          <span className="drop d3" />
          <span className="drop d4" />
          <span className="drop d5" />
          <span className="drop d6" />
          <span className="drop d7" />
          <span className="drop d8" />
          <span className="drop d9" />
          <span className="drop d10" />
          <span className="drop d11" />
          <span className="drop d12" />
          <span className="drop d13" />
          <span className="drop d14" />
          <span className="drop d15" />
          <span className="drop d16" />
          <span className="drop d17" />
          <span className="drop d18" />
        </div>
        <div className="nav-links">
          <Link to="/">Home</Link>
          <a href="/uplod" onClick={handleUploadNavClick}>
            Upload
          </a>
          <Link to="/history">History</Link>
          <Link to="/analytics">Analytics</Link>
          <Link to="/premium">Premium</Link>
          <a href="/mock-test" onClick={handleMockTestNavClick}>
            Mock Test{" "}
            {!premium.canUse("mock_exam") && <CrownIcon className="nav-premium-crown" />}
          </a>
          {!user && (
            <Link className="auth-btn" to="/login">
              Login
            </Link>
          )}
          {user && (
            <button className="auth-btn" type="button" onClick={handleLogout}>
              Logout
            </button>
          )}
          <img
            className="status-cloud"
            src={user ? "/happy.png" : "/sad.png"}
            alt={user ? "Happy cloud (logged in)" : "Sad cloud (logged out)"}
            title={user ? "Logged in" : "Logged out"}
          />
        </div>
      </nav>

      <Routes>
        <Route
          path="/"
          element={
            <main id="home" className="home-page">
              <div className="home-bots" aria-hidden="true">
                <div className="boat-group">
                  <img src="/blue.png" alt="" className="bot boat boat-blue" />
                </div>
              </div>
              <section className="hero-card">
                <h1>Welcome to EduCator</h1>
                <p>Learn with confidence and upload your study materials in one place.</p>
                <div className="hero-actions">
                  <button type="button" onClick={openUpload}>
                    Lets Start
                  </button>
                </div>
              </section>
            </main>
          }
        />
        <Route path="/login" element={<Login user={user} />} />
        <Route
          path="/uplod"
          element={
            <ProtectedRoute user={user}>
              <UploadPage user={user} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/mock-test"
          element={
            <ProtectedRoute user={user}>
              <MockTestPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/premium"
          element={
            <ProtectedRoute user={user}>
              <PremiumPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/youtube-guide"
          element={
            <ProtectedRoute user={user}>
              <YouTubeGuidePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/study-set"
          element={
            <ProtectedRoute user={user}>
              <StudySetPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/mcqs"
          element={
            <ProtectedRoute user={user}>
              <McqPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute user={user}>
              <HistoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute user={user}>
              <AnalyticsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/flashcards"
          element={
            <ProtectedRoute user={user}>
              <FlashcardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/summary"
          element={
            <ProtectedRoute user={user}>
              <SummaryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/fill-blanks"
          element={
            <ProtectedRoute user={user}>
              <FillBlanksPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/true-false"
          element={
            <ProtectedRoute user={user}>
              <TrueFalsePage />
            </ProtectedRoute>
          }
        />
        <Route
<<<<<<< HEAD
          path="/exam-mock"
          element={
            <ProtectedRoute user={user}>
              <ExamMockPage />
=======
          path="/match-the-pair"
          element={
            <ProtectedRoute user={user}>
              <MatchThePairPage />
>>>>>>> 5880e86 (Project ready)
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <ToastContainer position="bottom-right" autoClose={2500} />
    </div>
  );
}

function ProtectedRoute({ user, children }) {
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}

export default App;
