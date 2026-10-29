import React, { useEffect, useState } from 'react';
import CircularProgress from '@mui/material/CircularProgress';
import '../styles/components/PageLoader.css';

// Centered spinner for pages that are fetching data. It waits a moment before
// appearing, so quick loads don't flash anything at all.
const PageLoader = ({ delay = 300, size = 40, inline = false }) => {
  const [visible, setVisible] = useState(delay === 0);

  useEffect(() => {
    if (delay === 0) {
      return undefined;
    }
    const timer = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div className={inline ? 'page-loader page-loader-inline' : 'page-loader'} role="status" aria-label="Loading">
      {/* disableShrink keeps a full arc spinning, so it's visible from the first frame */}
      {visible && <CircularProgress disableShrink size={size} thickness={4} sx={{ color: '#2E3D34' }} />}
    </div>
  );
};

export default PageLoader;
