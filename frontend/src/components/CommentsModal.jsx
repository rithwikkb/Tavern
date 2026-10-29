// Import necessary libraries and components
import React, { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import { Comment } from '@mui/icons-material';
import Typography from '@mui/material/Typography';
import Modal from '@mui/material/Modal';
import Cookies from 'js-cookie';
import { Link } from 'react-router-dom'; // Import Link for navigation
import { getComments, createCommentLocal } from '../services/CommentsService';
import { getCurrentAuthor } from '../services/AuthorsService';
import '../styles/components/CommentsModal.css';

const CommentsModal = ({ postId, initialCount }) => {
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

      // Map fetched comments to have the author name and comment
      const mappedComments = fetchedComments.src.map((comment) => ({
        comment: comment.comment,
        displayName: comment.author.displayName,
        authorId: comment.author.id.replace(/\/$/, '').split('/').slice(-1)[0], // Extracting authorId from URL
      }));

      setComments(mappedComments);
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
      setComments([...comments, { comment: newComment, displayName: currentProfileData.displayName, authorId }]);
      setCommentsLength((prevLength) => prevLength + 1); // Increment comment count
      setNewComment(''); // Clear input after posting
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
              <Typography variant="body1">Loading comments...</Typography>
            ) : comments.length > 0 ? (
              comments.map((comment, index) => (
                <div key={index} className="comment-box">
                  <Typography className="comment-author">
                    {/* Author name as a clickable link */}
                    <Link to={`/profile/${comment.authorId}`} className="author-link">
                      {comment.displayName}
                    </Link>
                  </Typography>
                  <Typography className="comment-body">
                    {comment.comment}
                  </Typography>
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
