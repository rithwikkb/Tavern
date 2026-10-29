// https://bbbootstrap.com/snippets/delete-button-hover-effect-68431542
import PageLoader from '../components/PageLoader';
import React, { useState, useRef, useEffect } from 'react';
import '../styles/pages/Post.css';
import { ReactComponent as ImageUploader } from './../assets/imageUploader.svg';
import MarkdownEditor from '../components/MarkdownEditor';
import { createPost, getPost, updatePost } from '../services/PostsService';
import { prepareImageForPost } from '../utils/prepareImage';
import Cookies from 'js-cookie';
import { useParams, useNavigate } from 'react-router-dom';

const Post = () => {
  //#region Properties
  const authorId = Cookies.get('author_id');
  const { postId } = useParams();
  const navigate = useNavigate();
  const [visibility, setVisibility] = useState('public');
  const [selectedOption, setSelectedOption] = useState('Plain');

  const options = ['Plain', 'Markdown', 'Image'];
  const [title, setTitle] = useState('');
  const [uploadedImage, setUploadedImage] = useState(null);
  const [imgFile, setImgFile] = useState(null);
  // when editing an image post, its current image (kept unless a new one is chosen)
  const [existingImage, setExistingImage] = useState(null);
  const fileInputUpload = useRef(null);
  const [plainText, setPlainText] = useState('');
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(Boolean(postId));
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  //#endregion

  //#region Fetch Post Data (for editing)
  useEffect(() => {
    if (!postId) {
      return;
    }
    getPost(authorId, postId)
      .then((response) => {
        const post = response.data;
        setTitle(post.title || '');
        if (post.contentType === 'text/markdown') {
          setMarkdown(post.content || '');
          setSelectedOption('Markdown');
        } else if (post.contentType?.startsWith('image/')) {
          setExistingImage({ content: post.content, contentType: post.contentType });
          setUploadedImage(post.content.startsWith('data:') ? post.content : `data:${post.contentType},${post.content}`);
          setSelectedOption('Image');
        } else {
          setPlainText(post.content || '');
          setSelectedOption('Plain');
        }
        setVisibility(post.visibility.toLowerCase());
      })
      .catch((error) => {
        console.error('Error fetching post:', error);
        setError("Couldn't load this post.");
      })
      .finally(() => setLoading(false));
  }, [postId, authorId]);
  //#endregion

  //#region Event Handlers
  const handleVisibilityChange = (event) => {
    setVisibility(event.target.value);
  };
  const handleOptionClick = (option) => {
    setSelectedOption(option);
  };

  const handleImageUploaderClick = () => {
    fileInputUpload.current.click();
  };
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      setUploadedImage(imageUrl);
      setImgFile(file);
    }
  };

  const handlePlainTextChange = (event) => {
    setPlainText(event.target.value);
  };

  const handlePostClick = async () => {
    setError('');
    const postData = {
      type: 'post',
      title: title || 'New Post',
      visibility: visibility.toUpperCase(),
    };
    if (selectedOption === 'Plain') {
      postData.content = plainText;
      postData.contentType = 'text/plain';
    } else if (selectedOption === 'Markdown') {
      postData.content = markdown;
      postData.contentType = 'text/markdown';
    } else if (selectedOption === 'Image') {
      if (!imgFile && !existingImage) {
        setError('Choose an image to post.');
        return;
      }
    }

    setSubmitting(true);
    try {
      if (selectedOption === 'Image') {
        // a newly chosen image is shrunk to fit the upload limit; otherwise keep the current one
        const { content, contentType } = imgFile ? await prepareImageForPost(imgFile) : existingImage;
        postData.content = content;
        postData.contentType = contentType;
      }

      if (postId) {
        const currentDateTime = new Date().toISOString();
        postData.published = currentDateTime;
        // Update post if postId exists
        await updatePost(authorId, postId, postData);
      } else {
        // Create a new post if no postId
        await createPost(authorId, postData);
      }
      navigate(`/profile/${authorId}`);
    } catch (error) {
      console.error('Error during post creation/updating:', error);
      setError(
        error.response?.data?.error ||
          (error.response ? "Couldn't save the post. Please try again." : error.message) ||
          "Couldn't save the post. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteClick = async () => {
    if (!window.confirm("Delete this post? This can't be undone.")) {
      return;
    }
    try {
      // Change post visibility to 'DELETED'
      const authorId = Cookies.get('author_id');

      if (!authorId) {
        throw new Error('Author ID is missing.'); // Handle case where author_id is not available
      }
      const postData = { visibility: 'DELETED', author: authorId }; // Include author_id in the request
      const response = await updatePost(authorId, postId, postData); // Update the post's visibility

      if (response.status !== 200) {
        throw new Error('Failed to mark post as deleted.');
      }
      navigate('/');
    } catch (error) {
      console.error('Error deleting post:', error);
    }
  };
  //#endregion

  if (loading) {
    return <PageLoader />; // Display a loading state while the post data is being fetched
  }

  //#region Render
  const renderOption = (option) => (
    <button
      type="button"
      key={option}
      role="tab"
      aria-selected={selectedOption === option}
      className={selectedOption === option ? 'post-type-tab active' : 'post-type-tab'}
      onClick={() => handleOptionClick(option)}
    >
      {option}
    </button>
  );
  //#endregion

  return (
    <div className="posts-page">
      <div className="top-container">
        <h1>{postId ? 'Edit' : 'Create'} Post</h1>
        <div className="posts-options" role="tablist" aria-label="Post type">{options.map(renderOption)}</div>
      </div>

      <input
        type="text"
        id="title-input"
        placeholder="Title"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
      ></input>

      {selectedOption === 'Image' ? (
        <div id="image-selection-container" onClick={handleImageUploaderClick}>
          {uploadedImage ? (
            <img
              src={uploadedImage}
              alt="Uploaded"
              className="uploaded-image"
            />
          ) : (
            <>
              <ImageUploader className="image-uploader-svg" />
              <p id="image-selection-hint">Click to choose an image</p>
            </>
          )}
          <input
            type="file"
            ref={fileInputUpload}
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
        </div>
      ) : selectedOption === 'Plain' ? (
        <textarea
          id="plain-textarea"
          placeholder="Type something here..."
          value={plainText}
          onChange={handlePlainTextChange}
        ></textarea>
      ) : (
        <MarkdownEditor
          markdown={markdown}
          setMarkdown={setMarkdown}
        />
      )}

      <p className="visibility-heading">Who can see this?</p>
      <div className="visibility-options">
        <label className="radio-button">
          <input
            type="radio"
            name="visibility"
            value="public"
            checked={visibility === 'public'}
            onChange={handleVisibilityChange}
          />
          Public <span></span>
        </label>
        <label className="radio-button">
          <input
            type="radio"
            name="visibility"
            value="friends"
            checked={visibility === 'friends'}
            onChange={handleVisibilityChange}
          />
          Friends <span></span>
        </label>
        <label className="radio-button">
          <input
            type="radio"
            name="visibility"
            value="unlisted"
            checked={visibility === 'unlisted'}
            onChange={handleVisibilityChange}
          />
          Unlisted <span></span>
        </label>
      </div>

      {error && <div className="post-error" role="alert">{error}</div>}
      <div className="postPage-buttons">
        <button className="post-button" onClick={handlePostClick} disabled={submitting}>
          {/* editing an existing post saves it; anything else publishes a new one */}
          {submitting ? (postId ? 'Saving...' : 'Posting...') : (postId ? 'Save' : 'Post')}
        </button>
        {postId && (
          <button className="delete-button" onClick={handleDeleteClick}>
            <span className="text">Delete</span>
            <span className="icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
              >
                <path d="M24 20.188l-8.315-8.209 8.2-8.282-3.697-3.697-8.212 8.318-8.31-8.203-3.666 3.666 8.321 8.24-8.206 8.313 3.666 3.666 8.237-8.318 8.285 8.203z"></path>
              </svg>
            </span>
          </button>
        )}
      </div>
    </div>
  );
};

export default Post;
