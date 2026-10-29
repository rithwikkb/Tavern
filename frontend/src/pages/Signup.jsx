import React, { useState } from 'react';
import Cookies from 'js-cookie';
import { signup } from '../services/signupservice';
import { login } from '../services/loginservice';
import { useNavigate } from 'react-router-dom';
import '../styles/pages/Signup.css';
import SignUpImg from '../assets/signupImg.png';
import appLogo from  '../assets/Logo.png'

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
  const navigate = useNavigate();

  // Handle form field changes
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  // Handle image upload as soon as the user selects the image
  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    const username = formData.username; // Get the username

    if (file && username) {
      setImageUploading(true);

      const formDataToUpload = new FormData();
      formDataToUpload.append('profile_image', file);

      try {
        // Upload image to the server
        const response = await fetch(
          `${currentHost}/authors/${username}/upload_image/`,
          {
            method: 'POST',
            body: formDataToUpload,
          }
        );

        const result = await response.json();
        if (response.ok) {
          setFormData({
            ...formData,
            profileImage: result.url, // Store the image URL in the form data
          });
        } else {
          setError(result.message || 'Image upload failed.');
        }
      } catch (err) {
        console.error('Image upload error:', err);
        setError('Image upload failed.');
      } finally {
        setImageUploading(false);
      }
    } else {
      setError('Please enter a username before uploading an image.');
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
      Cookies.set('author_id', author_id);
      Cookies.set('access_token', access_token);
      Cookies.set('refresh_token', refresh_token);
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
        <img className= "image-log" src={ SignUpImg } alt="Signup image" />
      </div>
      <div className="signup-container">
        <h1 className="login-title">Sign Up</h1>

        {error && <div className="error-message">{error}</div>}
        <form className="form-container" onSubmit={handleSubmit}>
          <div className='form-signup'>
            <div className="form-group">
              <label className="input-label">Name</label>
              <input className='signup-inputLable'
                type="text"
                name="displayName"
                value={formData.displayName}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label className="input-label">Password</label>
              <input className='signup-inputLable'
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className='form-signup'>
            <div className="form-group">
              <label className="input-label">Username</label>
              <input className='signup-inputLable'
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="input-label">Email</label>
              <input className='signup-inputLable'
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className='form-signup'>
            <div className="form-group">
              <label className="input-label">GitHub</label>
              <input className='signup-inputLable'
                type="text"
                name="github"
                value={formData.github}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label className="input-label">Profile Image</label>
              <input className='signup-inputLable'
                id="file-input"
                type="file"
                name="profile_image"
                accept="image/*"
                onChange={handleImageUpload}
              />
              {imageUploading && <p>Uploading image...</p>}
              {formData.profileImage && <p>Image uploaded successfully.</p>}
            </div>
          </div>
     
          <button className="login-button" type="submit" disabled={loading}>
            {loading ? 'Signing Up...' : 'Sign Up'}
          </button>
        </form>
        <div className="signup-link">
          Have an account?{' '}
          <span onClick={() => navigate('/login')}>Log In</span>
        </div>
      </div>
    </div>
  );
};

export default Signup;

