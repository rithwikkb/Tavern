// Import necessary libraries and components
import PageLoader from './PageLoader';
import React, { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import { Comment, DeleteOutline } from '@mui/icons-material';
import Typography from '@mui/material/Typography';
import Modal from '@mui/material/Modal';
import Cookies from 'js-cookie';
import { Link } from 'react-router-dom'; // Import Link for navigation
import { getComments, createCommentLocal, deleteComment } from '../services/CommentsService';
import { fullDate, timeAgo } from '../utils/timeAgo';
import unknownUser from '../assets/unknownUser.png';
import { getCurrentAuthor } from '../services/AuthorsService';
import '../styles/components/CommentsModal.css';

// the last path segment of an API id like .../authors/<a>/commented/<c>
const serialOf = (id) => id.replace(/\/$/, '').split('/').pop();

// flatten an API comment into what the list needs
const toListItem = (comment) => ({
  id: serialOf(comment.id),
  comment: comment.comment,
  published: comment.published,
  displayName: comment.author.displayName,
  profileImage: comment.author.profileImage,
  authorId: serialOf(comment.author.id),
});

const CommentsModal = ({ postId, postAuthorId, initialCount }) => {
  const authorId = Cookies.get('author_id');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [comments, setComments] = useState([]);
  const [commentsLoaded, setCommentsLoaded] = useState(false);
  const [newComment, setNewComment] = useState('');
  // the feed and profile include each post's comment count, so the list itself only loads when opened
  const [commentsLength, setCommentsLength] = useState(initialCount ?? 0);

  const fetchComments = async () => {
    try {
      const fetchedComments = await getComments(authorId, postId);
      if (!fetchedComments) {
        return;
      }

      // the API lists newest first; show them oldest first like a conversation
      setComments(fetchedComments.src.map(toListItem).reverse());
      setCommentsLength(fetchedComments.count);
      setCommentsLoaded(true);
    } catch (error) {
      console.error(error);
    }
  };

  // posts that didn't come with a comment count (e.g. a single shared post) fetch it up front
  useEffect(() => {
    if (initialCount === undefined) {
      fetchComments();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId, initialCount]);

  // Open modal handler
  const handleOpen = async () => {
    setIsModalOpen(true);
    if (!commentsLoaded) {
      fetchComments();
    }
  };

  // Close modal handler
  const handleClose = () => setIsModalOpen(false);

  // Handle new comment submission
  const handleCommentSubmit = async () => {
    if (newComment.trim()) {
      const currentHost = window.location.origin; // Get host for post URL
      const currentProfileData = await getCurrentAuthor(authorId);
      const commentData = {
        type: 'comment',
        author: currentProfileData,
        comment: newComment,
        contentType: 'text/plain',
        post: `${currentHost}/api/authors/${authorId}/posts/${postId}/`,
      };
      const response = await createCommentLocal(authorId, commentData);
      if (!response) {
        return; // request failed; keep the text so the user can retry
      }
      setComments([...comments, toListItem(response)]);
      setCommentsLength((prevLength) => prevLength + 1); // Increment comment count
      setNewComment(''); // Clear input after posting
    }
  };

  // you can delete your own comments, and any comment on your own post
  const handleDelete = async (comment) => {
    if (!window.confirm('Delete this comment?')) {
      return;
    }
    if (await deleteComment(comment.authorId, comment.id)) {
      setComments(comments.filter((c) => c.id !== comment.id));
      setCommentsLength((prevLength) => prevLength - 1);
    }
  };

  return (
    <>
      <Modal
        open={isModalOpen}
        onClose={handleClose}
        aria-labelledby="comments-modal-title"
        aria-describedby="comments-modal-description"
      >
        <Box className={'modalBox'}>
          <Typography id="comments-modal-title" variant="h6" component="h2">
            Comments
          </Typography>
          <div className="comments-container">
            {!commentsLoaded ? (
              <PageLoader inline size={28} delay={150} />
            ) : comments.length > 0 ? (
              comments.map((comment) => (
                <div key={comment.id} className="comment-box">
                  <Link to={`/profile/${comment.authorId}`} className="comment-avatar" onClick={handleClose}>
                    <img src={comment.profileImage || unknownUser} alt="" loading="lazy" />
                  </Link>
                  <div className="comment-main">
                    <div className="comment-header">
                      <Link to={`/profile/${comment.authorId}`} className="author-link" onClick={handleClose}>
                        {comment.displayName}
                      </Link>
                      <span className="comment-time" title={fullDate(comment.published)}>
                        {timeAgo(comment.published)}
                      </span>
                      {(comment.authorId === authorId || postAuthorId === authorId) && (
                        <button
                          className="comment-delete"
                          aria-label="Delete comment"
                          title="Delete comment"
                          onClick={() => handleDelete(comment)}
                        >
                          <DeleteOutline fontSize="small" />
                        </button>
                      )}
                    </div>
                    <Typography className="comment-body">{comment.comment}</Typography>
                  </div>
                </div>
              ))
            ) : (
              <Typography variant="body1">No comments available.</Typography>
            )}
          </div>

          <div className="comment-input-box">
            <textarea
              className="comment-textbox"
              type="text"
              placeholder="Add a comment..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
            ></textarea>
            <button className="post-comment" onClick={handleCommentSubmit}>
              Post
            </button>
          </div>
        </Box>
      </Modal>

      <div
        className="comments-button-container"
        style={{ display: 'flex', alignItems: 'center' }}
      >
        <button className="comments-button" onClick={handleOpen}>
          <Comment />
        </button>
        <p className="comments-text">
          {commentsLength} {commentsLength === 1 ? 'comment' : 'comments'}
        </p>
      </div>
    </>
  );
};

export default CommentsModal;
