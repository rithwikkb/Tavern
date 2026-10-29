import React, { useState } from 'react';
import { setAuthCookies } from '../utils/authCookies';
import { signup } from '../services/signupservice';
import { login } from '../services/loginservice';
import { useNavigate } from 'react-router-dom';
import '../styles/pages/Signup.css';
import SignUpImg from '../assets/signupImg.png';
import appLogo from  '../assets/Logo.png'
import ImagePicker from '../components/ImagePicker';

const Signup = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    displayName: '',
    github: '',
    profileImage: '', // Will store the image file
  });

  const currentHost = window.location.origin; 
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [imageUploading, setImageUploading] = useState(false); // State for tracking image upload
  const [imageError, setImageError] = useState('');
  const navigate = useNavigate();

  // Handle form field changes
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  // Upload the picture as soon as it's chosen, so signup only has to send its URL
  const handleImageUpload = async (file) => {
    setImageUploading(true);
    setImageError('');

    const formDataToUpload = new FormData();
    formDataToUpload.append('profile_image', file);

    try {
      // the username in this URL isn't used for anything, so it doesn't need to be filled in yet
      const response = await fetch(
        `${currentHost}/authors/${encodeURIComponent(formData.username || 'new-user')}/upload_image/`,
        {
          method: 'POST',
          body: formDataToUpload,
        }
      );

      const result = await response.json();
      if (response.ok) {
        // functional update so fields typed during the upload aren't lost
        setFormData((current) => ({ ...current, profileImage: result.url }));
      } else {
        setImageError(result.error || result.detail || 'Image upload failed.');
      }
    } catch (err) {
      console.error('Image upload error:', err);
      setImageError('Image upload failed.');
    } finally {
      setImageUploading(false);
    }
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Submit the form data (with the uploaded profile image URL)
      await signup(formData);
    } catch (err) {
      setError(err.message || 'Signup failed. Please try again.');
      setLoading(false);
      return;
    }

    try {
      // Log the new user straight in so they land on their feed
      const { refresh_token, access_token, author_id } = await login({
        username: formData.username,
        password: formData.password,
      });
      setAuthCookies({ authorId: author_id, accessToken: access_token, refreshToken: refresh_token, isDemo: false });
      navigate('/');
    } catch (err) {
      // account was created but auto-login failed; let them log in manually
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="signup-background-container"
      id="signup-background-container"
    >
      <div className='signup-image'>
      <img className='logoSignup' src = { appLogo } alt='logo Img' />
        <img className= "image-log" src={ SignUpImg } alt="" />
      </div>
      <div className="signup-container">
        <div className="signup-card">
          <h1 className="login-title">Sign Up</h1>
          <p className="signup-subtitle">Create an account to post, follow people and join the conversation.</p>

          {error && <div className="error-message" role="alert">{error}</div>}
          <form className="signup-form" onSubmit={handleSubmit}>
            <div className="signup-grid">
              <div className="signup-field">
                <label className="input-label" htmlFor="signup-display-name">Display name</label>
                <input
                  id="signup-display-name"
                  type="text"
                  name="displayName"
                  autoComplete="name"
                  value={formData.displayName}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="signup-field">
                <label className="input-label" htmlFor="signup-username">Username</label>
                <input
                  id="signup-username"
                  type="text"
                  name="username"
                  autoComplete="username"
                  value={formData.username}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="signup-field">
                <label className="input-label" htmlFor="signup-email">Email</label>
                <input
                  id="signup-email"
                  type="email"
                  name="email"
                  autoComplete="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="signup-field">
                <label className="input-label" htmlFor="signup-password">Password</label>
                <input
                  id="signup-password"
                  type="password"
                  name="password"
                  autoComplete="new-password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                />
                <small className="field-hint">
                  At least 8 characters, not all numbers, and not a common password.
                </small>
              </div>

              <div className="signup-field">
                <label className="input-label" htmlFor="signup-github">
                  GitHub link <span className="optional-tag">optional</span>
                </label>
                <input
                  id="signup-github"
                  type="url"
                  name="github"
                  placeholder="https://github.com/you"
                  value={formData.github}
                  onChange={handleChange}
                />
              </div>

              <div className="signup-field">
                <span className="input-label">
                  Profile picture <span className="optional-tag">optional</span>
                </span>
                <ImagePicker
                  imageUrl={formData.profileImage}
                  uploading={imageUploading}
                  error={imageError}
                  onFileSelected={handleImageUpload}
                />
              </div>
            </div>

            <button className="login-button signup-submit" type="submit" disabled={loading || imageUploading}>
              {loading ? 'Signing up...' : 'Sign Up'}
            </button>
          </form>
          <div className="signup-link">
            Have an account?{' '}
            <span onClick={() => navigate('/login')}>Log In</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Signup;

