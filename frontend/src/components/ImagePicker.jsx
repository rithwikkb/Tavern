import React, { useRef, useState } from 'react';
import CircularProgress from '@mui/material/CircularProgress';
import unknownUser from '../assets/unknownUser.png';
import '../styles/components/ImagePicker.css';

// Profile picture picker: a round preview and a "Choose picture" button,
// instead of the browser's plain "Choose file / No file chosen" control.
const ImagePicker = ({ imageUrl, uploading, error, onFileSelected, label = 'Profile picture' }) => {
  const fileInput = useRef(null);
  // an existing picture (e.g. when editing a profile) isn't something the user just chose
  const [picked, setPicked] = useState(false);

  const handleChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setPicked(true);
      onFileSelected(file);
    }
    // allow choosing the same file again after an error
    event.target.value = '';
  };

  let status = 'PNG, JPEG or GIF, up to 5 MB';
  if (uploading) {
    status = 'Uploading…';
  } else if (error) {
    status = error;
  } else if (imageUrl && picked) {
    status = 'Looks good! Choose another to replace it.';
  }

  return (
    <div className="image-picker">
      <div className="image-picker-preview">
        <img src={imageUrl || unknownUser} alt="" />
        {uploading && (
          <div className="image-picker-overlay">
            <CircularProgress disableShrink size={24} thickness={5} sx={{ color: '#f7ebc9' }} />
          </div>
        )}
      </div>
      <div className="image-picker-body">
        <button
          type="button"
          className="image-picker-button"
          onClick={() => fileInput.current.click()}
          disabled={uploading}
          aria-label={`${imageUrl ? 'Change' : 'Choose'} ${label.toLowerCase()}`}
        >
          {imageUrl ? 'Change picture' : 'Choose picture'}
        </button>
        <p className={error ? 'image-picker-status image-picker-error' : 'image-picker-status'} role={error ? 'alert' : undefined}>
          {status}
        </p>
      </div>
      <input
        ref={fileInput}
        type="file"
        accept="image/png,image/jpeg,image/gif"
        onChange={handleChange}
        hidden
      />
    </div>
  );
};

export default ImagePicker;
