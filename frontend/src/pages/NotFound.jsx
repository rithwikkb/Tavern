import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/pages/NotFound.css';

// Shown for any URL the app doesn't know, instead of an empty page
const NotFound = () => (
  <div className="not-found">
    <h1>Page not found</h1>
    <p>This page doesn't exist, or the link is out of date.</p>
    <Link className="not-found-home" to="/">
      Go to the home feed
    </Link>
  </div>
);

export default NotFound;
