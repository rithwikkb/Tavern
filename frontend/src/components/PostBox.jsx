import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getMarkdownText } from '../utils/getMarkdownText';
import { fullDate, timeAgo } from '../utils/timeAgo';
import '../styles/components/PostBox.css';
import LikeButton from './LikeButton';
import CommentsModal from './CommentsModal';
import { BorderColor } from '@mui/icons-material';
import shareLinkIcon from '../assets/share_link.png';
import unknownUser from  '../assets/unknownUser.png';

const PostBox = ({ post, poster, isUserEditable }) => {
  const [showCopyNotification, setShowCopyNotification] = useState(false); // State for notification
  const navigate = useNavigate();

  const authorId = post.author.id.split('/')[5];
  const postSerial = post.id.split('/').filter(Boolean).pop();
  const posterName = poster?.displayName || 'Anonymous';
  const posterImageUrl = poster?.profileImage || unknownUser;
  const postLink = `${window.location.origin}/post/${postSerial}`;

  const handleCopyLink = () => {
    navigator.clipboard
      .writeText(postLink)
      .then(() => {
        setShowCopyNotification(true);
        setTimeout(() => setShowCopyNotification(false), 2000); // Hide notification after 2 seconds
      })
      .catch((err) => console.error('Failed to copy link: ', err));
  };

  return (
    <div className="post-box">
      <div className="post-header">
        <Link to={`/profile/${authorId}`} style={{ display: 'flex' }}>
          <div className="profile-image-container">
            <img
              src={posterImageUrl}
              alt=""
              className="profile-image"
              loading="lazy"
            />
          </div>
        </Link>
        <div className="poster-name-date">
          <Link to={`/profile/${authorId}`} className="poster-name-link">
            <h4>{posterName}</h4>
          </Link>
          <p title={fullDate(post.published)}>{timeAgo(post.published)}</p>
        </div>
        {isUserEditable && (
          <div className="post-edit">
            <button
              className="post-edit-button"
              aria-label="Edit post"
              onClick={() => navigate(`/post/${postSerial}/edit`, { state: { postId: postSerial } })}
            >
              <BorderColor className="post-edit-icon" />
            </button>
          </div>
        )}
      </div>
      <div className="post-content">
        <h2>{post.title}</h2>
        {post.contentType === 'text/plain' && <p>{post.content}</p>}
        {post.contentType?.startsWith('image/') && (
          <img
            src={`${post.content.startsWith('data:') ? '' : `data:${post.contentType},`}${post.content}`}
            alt={post.title || 'Post image'}
          />
        )}
        {post.contentType === 'text/markdown' && (
          <div className="post-markdown" dangerouslySetInnerHTML={getMarkdownText(post.content)} />
        )}
      </div>

      <div className="post-footer">
        <LikeButton post={post} />
        <CommentsModal postId={post.id} initialCount={post.comments_count} />
        <button onClick={handleCopyLink} className="share-link-button">
          <img
            src={shareLinkIcon}
            alt=""
            className="share-link-icon"
          />
          <span>Share Link</span>
        </button>
        {showCopyNotification && (
          <span className="copy-notification">Post link copied!</span>
        )}
      </div>
    </div>
  );
};

export default PostBox;
