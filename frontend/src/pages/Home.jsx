import React, { useState, useEffect, useRef } from 'react';
import PageLoader from '../components/PageLoader';
import '../styles/pages/Home.css';
import FollowRequests from '../components/FollowRequests';
import SearchBar from '../components/SearchBar';
import SearchResultsList from '../components/SearchResultsList';
import { makeGithubActivityPosts } from '../services/GithubService';
import Cookies from 'js-cookie';
import api from '../services/axios';
import PostBox from '../components/PostBox';

const Home = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [results, setResults] = useState([]);
  const hasRun = useRef(false);
  const searchArea = useRef(null);
  const [searchOpen, setSearchOpen] = useState(false);

  // close the search results when clicking elsewhere or pressing Escape
  useEffect(() => {
    const handleClick = (event) => {
      if (searchArea.current && !searchArea.current.contains(event.target)) {
        setSearchOpen(false);
      }
    };
    const handleKey = (event) => {
      if (event.key === 'Escape') {
        setSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, []);

  useEffect(() => {
    if (hasRun.current) {
      return;
    }
    hasRun.current = true;
    const makeGithubActivityPostsFromService = async () => {
      const authorId = Cookies.get('author_id');
      if (!authorId) {
        return;
      }
      await makeGithubActivityPosts(authorId);
    };

    makeGithubActivityPostsFromService();
  }, []);

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        // the server only returns posts you're allowed to see, newest first
        const response = await api.get('posts/');
        setPosts(response.data.posts);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPosts();
  }, []);

  if (loading) {
    return <PageLoader />;
  }

  if (error) {
    return <p>Error: {error}</p>;
  }

  return (
    <div className="home-page-container">
      <div className="home-container">
        <h1>Feed</h1>
        <div
          className="search-area"
          ref={searchArea}
          onFocus={() => setSearchOpen(true)}
          onClick={() => setSearchOpen(true)}
          onInput={() => setSearchOpen(true)}
        >
          <SearchBar setResults={setResults} />
          {searchOpen && results.length > 0 && <SearchResultsList results={results} />}
        </div>
        <div className="posts-container">
          {posts.length > 0 ? (
            <ul>
              {posts.map((post) => (
                <li key={post.id}>
                  <PostBox post={post} poster={post.author} />
                </li>
              ))}
            </ul>
          ) : (
            <p>No posts available.</p>
          )}
        </div>
      </div>
      <div className="follow-request-container">
        <FollowRequests />
      </div>
    </div>
  );
};

export default Home;
