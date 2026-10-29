import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../services/axios';
import { getAuthorProfile } from '../services/profileService';
import PostBox from '../components/PostBox';

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
        const profile = await getAuthorProfile(postData.author.id.replace(/\/$/, '').split('/').pop());
        setAuthor(profile);
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
    return <p>Loading...</p>;
  }

  if (error) {
    return <p>{error}</p>;
  }

  return (
    <div>
      {post && author && (
        <PostBox post={post} poster={author} />
      )}
      {/* You can add more components here like comments, likes, etc. */}
    </div>
  );
};

export default PostDetail;
