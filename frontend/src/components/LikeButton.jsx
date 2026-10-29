//https://medium.com/@yuvidexter/%EF%B8%8Fadding-a-magical-like-button-to-your-react-js-464989211940 for like button jsx logic, Author: Yuvi Dexter, obtained 2024-10-19
// https://codepen.io/bnewton/pen/KMbLZx
import React, { useEffect, useState, useRef } from 'react';
import Cookies from 'js-cookie';
import { createLike, getLikes } from '../services/LikesService';
import { Favorite } from '@mui/icons-material';
import { getCurrentAuthor } from '../services/AuthorsService';
import '../styles/components/LikeButton.css';
import { Author } from '../models/Author';
import AuthorsListModal from '../components/AuthorsListModal';
import mojs from '@mojs/core';

const LikeButton = ({ post, posterId }) => {
  // the feed and profile include like counts with each post, so cards don't need a request each
  const [likesCount, setLikesCount] = useState(post.likes_count ?? 0);
  const [showAuthorsModal, setShowAuthorsModal] = useState(false);
  const [authorsList, setAuthorsList] = useState([]);
  const [isLiked, setIsLiked] = useState(post.liked_by_me ?? false);
  const authorId = Cookies.get('author_id');
  const buttonRef = useRef(null); 

  // Initialize animation
  useEffect(() => {
    const el = buttonRef.current;

    const scaleCurve = mojs.easing.path('M0,100 L25,99.9999983 C26.2328835,75.0708847 19.7847843,0 100,0');

    const burst1 = new mojs.Burst({
      parent: el,
      radius: { 0: 100 },
      angle: { 0: 45 },
      y: -10,
      count: 10,
      children: {
        shape: 'circle',
        radius: 30,
        fill: ['red', 'white'],
        strokeWidth: 15,
        duration: 500,
      },
    });

    const scaleAnimation = new mojs.Tween({
      duration: 900,
      onUpdate: (progress) => {
        const scaleProgress = scaleCurve(progress);
        el.style.transform = `scale3d(${scaleProgress}, ${scaleProgress}, 1)`;
      },
    });

    const burst2 = new mojs.Burst({
      parent: el,
      radius: { 0: 125 },
      angle: { 0: -45 },
      y: -10,
      count: 10,
      children: {
        shape: 'circle',
        radius: 30,
        fill: ['white', 'red'],
        strokeWidth: 15,
        duration: 400,
      },
    });

    const timeline = new mojs.Timeline();
    timeline.add(burst1, scaleAnimation, burst2);

    // Attach animation to the button click
    const animate = () => {
      if (!isLiked) {
        timeline.play();
      }
    };

    el.addEventListener('click', animate);

    return () => {
      el.removeEventListener('click', animate); // Cleanup event listener
    };
  }, [isLiked]);

  // posts that didn't come with like info (e.g. a single shared post) fetch it here
  useEffect(() => {
    if (post.likes_count !== undefined) {
      return;
    }
    const fetchLikes = async () => {
      try {
        const likesResponse = await getLikes(authorId, post.id);
        setLikesCount(likesResponse.count);
        // likes are paginated, so the server says directly whether this user liked the post
        setIsLiked(!!likesResponse.liked_by_me);
      } catch (error) {
        console.error(error);
      }
    };

    fetchLikes();
  }, [authorId, post.id, post.likes_count]);

  const handleLike = async () => {
    if (!isLiked) {
      //create like object
      const post_id = post.id.replace(/\/$/, '');
      const likeData = {
        type: 'like',
        author: await getCurrentAuthor(authorId),
        object: `${post_id}/`,
      };

      try {
        const response = await createLike(authorId, likeData);

        // only updating likes if request is successful
        if (response.status === 201) {
          setLikesCount(likesCount + 1);
          setIsLiked(true);
        } else if (response.status === 200) {
          console.log(response.data);
        } else {
          console.error('Creating like failed with ', response.status);
        }
      } catch (error) {
        console.error('Error handling like', error);
      }
    }
  };

  const handleShowAuthors = async () => {
    try {
      const likesResponse = await getLikes(authorId, post.id, 100) //hitting endpoint again because if you like, you'll have to call getLikes anyways

      // store authors who liked the post
      const authors = likesResponse.src.map(
        (like) =>
          new Author(
            like.author.id,
            like.author.host,
            like.author.displayName,
            like.author.github,
            like.author.profileImage,
            like.author.page
          )
      );
      setAuthorsList(authors);
      setShowAuthorsModal(true);
    } catch (error) {
      console.error(error);
    }
  }



  return (
    <div className="like-button-container">
      <button
        className={`like-button ${isLiked ? 'active' : ''}`}
        onClick={handleLike}
        ref={buttonRef}
      >
        <Favorite className={`like-heart ${isLiked ? 'liked' : 'not-liked'}`} />
      </button>
      <span className="like-text" onClick={handleShowAuthors}>
        {' '}
        {likesCount} {likesCount === 1 ? 'like' : 'likes'}
      </span>
      {showAuthorsModal && (
        <AuthorsListModal 
          authors={authorsList}
          onModalClose={() => setShowAuthorsModal(false)}
           />
      )}
    </div>
  );
};

export default LikeButton;