import React, { useState, useEffect } from 'react';
import PageLoader from '../components/PageLoader';
import { useParams } from 'react-router-dom';
import api from '../services/axios';
import PostBox from '../components/PostBox';
import '../styles/pages/PostDetail.css';

const PostDetail = () => {
  const { postId } = useParams(); // Get postId from URL parameters
  const [post, setPost] = useState(null);
  const [author, setAuthor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPostDetail = async () => {
      try {
        // the server only returns posts this user is allowed to see,
        // so unlisted posts work for anyone with the link
        const response = await api.get(`posts/${postId}/`);
        const postData = response.data;
        setPost(postData);
        // the post already includes its author's name and picture
        setAuthor(postData.author);
      } catch (err) {
        console.error('Error fetching post detail:', err.message);
        setError(
          err.response?.status === 404
            ? "This post doesn't exist or isn't shared with you."
            : 'Something went wrong loading this post.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchPostDetail();
  }, [postId]);

  if (loading) {
    return <PageLoader />;
  }

  if (error) {
    return <p className="post-detail-message">{error}</p>;
  }

  return (
    <div className="post-detail-page">
      {post && author && (
        <PostBox post={post} poster={author} />
      )}
    </div>
  );
};

export default PostDetail;
