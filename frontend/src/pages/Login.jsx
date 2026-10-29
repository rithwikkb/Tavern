import React, { useState } from 'react';
import { setAuthCookies } from '../utils/authCookies';
import '../styles/pages/Login.css';
import { login } from '../services/loginservice';
import { useNavigate } from 'react-router-dom';
import LogInImg from '../assets/LogInImg.png';
import appLogo from  '../assets/Logo.png'

// Public demo credentials; must match DEMO_USERNAME / DEMO_PASSWORD in the Django settings
const DEMO_USERNAME = 'demo';
const DEMO_PASSWORD = 'TavernDemo2026';

const Login = () => {
  //#region Properties
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const navigate = useNavigate();
  //#endregion

  //#region Event Handlers
  const logIn = async (loginData) => {
    try {
      setLoading(true);
      setError('');
      const response = await login(loginData);
      if (!response) {
        throw new Error('Login failed: No response');
      }
      const { refresh_token, access_token, author_id, is_demo } = response;

      setAuthCookies({ authorId: author_id, accessToken: access_token, refreshToken: refresh_token, isDemo: Boolean(is_demo) });

      navigate('/');
    } catch (error) {
      // show the server's reason (wrong credentials, inactive account) when there is one
      // `detail` carries DRF's message, e.g. when too many attempts are throttled
      setError(error.response?.data?.error || error.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await logIn({ username, password });
  };

  // one click into the shared demo account (created by `manage.py seed_demo`)
  const handleDemoLogin = async () => {
    await logIn({ username: DEMO_USERNAME, password: DEMO_PASSWORD });
  };
  //#endregion

  return (
    <div className="login-background-container">
      <div className='login-image'>
        <img className='logo' src = { appLogo } alt='logo Img' />
        <img className= "image-log" src={ LogInImg } alt="" />
      </div>
      <div className="login-container">
        <div className="login-intro">
          <p>
            <strong>Tavern</strong> is a small social network: share posts in plain text, Markdown or
            images, follow people, become friends, and comment on and like each other's posts.
          </p>
          <p className="login-intro-links">
            <a href="https://github.com/rithwikkb/Tavern_WebApp" target="_blank" rel="noopener noreferrer">
              Code on GitHub
            </a>
            <span aria-hidden="true"> · </span>
            <a href="/swagger/" target="_blank" rel="noopener noreferrer">
              API docs
            </a>
          </p>
        </div>
        <h1 className="login-title">Log In</h1>
        {error && <div className="error-message" role="alert">{error}</div>}
        <form className="form-container" onSubmit={handleSubmit} method="post">
          <div className="form-group">
            <label className="input-label">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="input-label">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button className="login-button" type="submit" disabled={loading}>
            {loading ? 'Logging in...' : 'Log In'}
          </button>
          {/* inside the form so it lines up with the Log In button; type="button" keeps it from submitting */}
          <div className="demo-login">
            <span className="demo-divider">or</span>
            <button className="demo-login-button" type="button" onClick={handleDemoLogin} disabled={loading}>
              Try the demo account
            </button>
            <p className="demo-credentials">
              Username <strong>{DEMO_USERNAME}</strong> · Password <strong>{DEMO_PASSWORD}</strong>
            </p>
          </div>
        </form>
        <div className="signup-link">
          No account? <span onClick={() => navigate('/signup')}>Sign Up</span>
        </div>
      </div>
    </div>
  );
};

export default Login;

