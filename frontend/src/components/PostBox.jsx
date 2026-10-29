import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Cookies from 'js-cookie';
import { getMarkdownText } from '../utils/getMarkdownText';
import { fullDate, timeAgo } from '../utils/timeAgo';
import '../styles/components/PostBox.css';
import LikeButton from './LikeButton';
import CommentsModal from './CommentsModal';
import { BorderColor, Group, Link as LinkIcon, Public } from '@mui/icons-material';
import shareLinkIcon from '../assets/share_link.png';
import unknownUser from  '../assets/unknownUser.png';

// who can see a post, shown next to its timestamp
const VISIBILITY = {
  PUBLIC: { label: 'Public', Icon: Public, hint: 'Anyone can see this post' },
  FRIENDS: { label: 'Friends', Icon: Group, hint: 'Only mutual friends can see this post' },
  UNLISTED: { label: 'Unlisted', Icon: LinkIcon, hint: 'Shown to followers and anyone with the link' },
};

const PostBox = ({ post, poster }) => {
  const [showCopyNotification, setShowCopyNotification] = useState(false); // State for notification
  const navigate = useNavigate();
  const location = useLocation();

  const authorId = post.author.id.split('/')[5];
  const postSerial = post.id.split('/').filter(Boolean).pop();
  const posterName = poster?.displayName || 'Anonymous';
  const posterImageUrl = poster?.profileImage || unknownUser;
  const postLink = `${window.location.origin}/post/${postSerial}`;
  // your own posts can be edited wherever they appear (feed, profiles, shared links)
  const isOwnPost = authorId === Cookies.get('author_id');
  const visibility = VISIBILITY[post.visibility];

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
          <div className="post-meta">
            <span title={fullDate(post.published)}>{timeAgo(post.published)}</span>
            {visibility && (
              <span className="post-visibility" title={visibility.hint}>
                <visibility.Icon className="post-visibility-icon" aria-hidden="true" />
                {visibility.label}
              </span>
            )}
          </div>
        </div>
        {isOwnPost && (
          <div className="post-edit">
            <button
              className="post-edit-button"
              aria-label="Edit post"
              // remember where the edit started so saving returns there
              onClick={() => navigate(`/post/${postSerial}/edit`, { state: { postId: postSerial, from: location.pathname } })}
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
        <CommentsModal postId={post.id} postAuthorId={authorId} initialCount={post.comments_count} />
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
