import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./App.css";
import { auth } from "./firebase";
import Login from "./components/auth/Login";
import UploadPage from "./components/upload/UploadPage";

function App() {
  const [message, setMessage] = useState("");
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setAuthReady(true);
    });

    return () => unsubscribe();
  }, []);

  const fetchMessage = async () => {
    try {
      const response = await fetch("http://127.0.0.1:5000/api/message");
      const data = await response.json();
      setMessage(data.message);
    } catch (error) {
      console.error("Error fetching message:", error);
    }
  };

  const openUpload = () => {
    if (!user) {
      toast.info("Login first");
      navigate("/login", { state: { from: "/uplod" } });
      return;
    }

    navigate("/uplod");
  };

  const handleUploadNavClick = (event) => {
    event.preventDefault();
    openUpload();
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
                {message && <p className="message">{message}</p>}
              </section>
            </main>
          }
        />
        <Route path="/login" element={<Login user={user} />} />
        <Route
          path="/uplod"
          element={
            <ProtectedRoute user={user}>
              <UploadPage />
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
