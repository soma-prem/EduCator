import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "firebase/auth";
import { toast } from "react-toastify";
import { auth, googleProvider } from "../../firebase";

function Login({ user }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/uplod";

  useEffect(() => {
    if (user) {
      navigate(from, { replace: true });
    }
  }, [user, from, navigate]);

  const onGoogleLogin = async () => {
    try {
      setPending(true);
      await signInWithPopup(auth, googleProvider);
      toast.success("Logged in with Google");
      navigate(from, { replace: true });
    } catch (error) {
      toast.error(error.message);
    } finally {
      setPending(false);
    }
  };

  const onEmailLogin = async () => {
    try {
      setPending(true);
      await signInWithEmailAndPassword(auth, email, password);
      toast.success("Logged in");
      navigate(from, { replace: true });
    } catch (error) {
      toast.error(error.message);
    } finally {
      setPending(false);
    }
  };

  const onEmailRegister = async () => {
    try {
      setPending(true);
      await createUserWithEmailAndPassword(auth, email, password);
      toast.success("Account created");
      navigate(from, { replace: true });
    } catch (error) {
      toast.error(error.message);
    } finally {
      setPending(false);
    }
  };

  const onSubmit = (event) => {
    event.preventDefault();
    onEmailLogin();
  };

  return (
    <main className="auth-page">
      <section className="auth-card auth-card-pro">
        <div className="auth-layout">
          <div className="auth-hero">
            <p className="auth-eyebrow">Welcome back</p>
            <h2>Sign in to EduCator</h2>
            <p className="auth-subtitle">
              Generate smart MCQs and flashcards from your study material in seconds.
            </p>
            <ul className="auth-points">
              <li>Fast study-set generation</li>
              <li>History saved to your account</li>
              <li>Works with files and text</li>
            </ul>
          </div>

          <div className="auth-panel">
            <button type="button" className="google-btn pro" onClick={onGoogleLogin} disabled={pending}>
              <span className="google-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" role="img">
                  <path
                    d="M23.5 12.3c0-.8-.1-1.4-.2-2.1H12v4h6.5c-.3 1.7-1.3 3.2-2.8 4.1v3.4h4.5c2.7-2.5 4.3-6.2 4.3-9.4z"
                    fill="#4285F4"
                  />
                  <path
                    d="M12 24c3.5 0 6.5-1.2 8.7-3.2l-4.5-3.4c-1.2.8-2.7 1.4-4.2 1.4-3.2 0-5.9-2.2-6.9-5.1H.6v3.2C2.8 21.7 7.1 24 12 24z"
                    fill="#34A853"
                  />
                  <path
                    d="M5.1 13.7c-.2-.6-.3-1.2-.3-1.9s.1-1.3.3-1.9V6.7H.6C.2 7.8 0 9 0 11.8s.2 4 1 5.1l4.1-3.2z"
                    fill="#FBBC05"
                  />
                  <path
                    d="M12 4.7c1.9 0 3.6.7 4.9 1.9l3.7-3.7C18.5 1 15.5 0 12 0 7.1 0 2.8 2.3.6 5.7l4.5 3.2C6.1 6.9 8.8 4.7 12 4.7z"
                    fill="#EA4335"
                  />
                </svg>
              </span>
              Continue with Google
            </button>

            <div className="auth-divider">
              <span>or continue with email</span>
            </div>

            <form onSubmit={onSubmit} className="auth-form">
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={6}
                required
              />
              <button type="submit" disabled={pending}>
                Login with Email
              </button>
              <button type="button" className="ghost-btn" onClick={onEmailRegister} disabled={pending}>
                Create Account
              </button>
            </form>
          </div>
        </div>
      </section>
    </main>
  );
}

export default Login;
