import React, { useState, useEffect } from 'react';
import PageLoader from '../components/PageLoader';
import { getAuthorProfile } from '../services/profileService';
import { getAuthor } from '../services/AuthorsService';
import FollowButton from '../components/FollowButton';
import '../styles/pages/Profile.css';
import Cookies from 'js-cookie';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import PostBox from '../components/PostBox';
import NotFound from './NotFound';
import { getFollowers } from '../services/FollowDetailService';
import { getFriends } from '../services/FriendsDetailService';
import { getFollowing } from '../services/FollowingDetailService';
import AuthorsListModal from '../components/AuthorsListModal';
import unknownUser from  '../assets/unknownUser.png';

const Profile = () => {
  const { authorId } = useParams();
  const currentUserId = Cookies.get('author_id');
  const [profileData, setProfileData] = useState(null);
  const [linkCopied, setLinkCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [profileNotFound, setProfileNotFound] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [modalData, setModalData] = useState([]);
  const [modalTitle, setModalTitle] = useState(''); // To display the title dynamically
  const [authorProfileData, setAuthorProfileData] = useState(null);
  const [authorCurrentData, setAuthorCurrentData] = useState(null);

  const navigate = useNavigate();
  const location = useLocation();

  // only the profile request decides when loading is done; the smaller author request
  // finishing first used to flash "Error loading profile data"
  useEffect(() => {
    setLoading(true);
    setProfileNotFound(false);
    getAuthorProfile(authorId)
      .then((data) => {
        setProfileData(data);
      })
      .catch((err) => {
        console.error(err);
        setProfileNotFound(err.response?.status === 404);
      })
      .finally(() => setLoading(false));
  }, [authorId]);
  
  useEffect(() => {
    getAuthor(authorId)
    .then((data) => {
      setAuthorProfileData(data);
    })
    .catch((err) => {
      console.error(err);
    });
  }, [authorId]);

  useEffect(() => {
    setShowModal(false);
  }, [location]);
  const closeModal = () => {
    setShowModal(false);
  };

  useEffect(() => {
    getAuthor(currentUserId)
    .then((data) => {
      setAuthorCurrentData(data);
    })
    .catch((error) => {
      console.error(error);
    });
  }, [currentUserId]);

  // Function to fetch followers and toggle the display
  const handleFollowersClick = async () => {
    try {
      const followersData = await getFollowers(authorId);
      setModalData(followersData.followers);
      setModalTitle('Followers');
      setShowModal(true);
    } catch (error) {
      console.error('Error fetching followers:', error);
    }
  };
  // Function to fetch friends and toggle the display
  const handleFriendsClick = async () => {
    try {
      const friendsData = await getFriends(authorId);
      setModalData(friendsData.friends);
      setModalTitle('Friends');
      setShowModal(true);
    } catch (error) {
      console.error('Error fetching friends:', error);
    }
  };

  const handleFollowingClick = async () => {
    try {
      const followingData = await getFollowing(authorId);
      setModalData(followingData.following);
      setModalTitle('Following');
      setShowModal(true);
    } catch (error) {
      console.error('Error fetching following:', error);
    }
  };

  if (loading) {
    return <PageLoader />;
  }

  if (profileNotFound) {
    return <NotFound />;
  }

  if (!profileData) {
    return <p>Couldn't load this profile. Please try again.</p>;
  }

  const isCurrentUser = currentUserId === authorId;

  // new accounts default to the bare "https://github.com/" link
  // share this profile without showing a long raw URL on the page
  const handleCopyProfileLink = () => {
    const profileUrl = `${window.location.origin}/profile/${profileData.id.replace(/\/$/, '').split('/').pop()}`;
    navigator.clipboard
      .writeText(profileUrl)
      .then(() => {
        setLinkCopied(true);
        setTimeout(() => setLinkCopied(false), 2000);
      })
      .catch((err) => console.error('Failed to copy link: ', err));
  };

  // only render real web links (never javascript: or other schemes)
  const hasGithub =
    /^https?:\/\//i.test(profileData.github || '') &&
    !/^https?:\/\/github\.com\/?$/.test(profileData.github);
  // one timeline of every post you're allowed to see, newest first; each card shows its visibility
  const posts = [
    ...(profileData.public_posts || []),
    ...(profileData.friends_posts || []),
    ...(profileData.unlisted_posts || []),
    ...(profileData.shared_posts || []),
  ].sort((a, b) => new Date(b.published) - new Date(a.published));

  return (
    <div className="profile-page">
      <div className="profile-header">
        <div className="Img-details">
          <img
            src={profileData.profileImage || unknownUser}
            alt={profileData.displayName}
            className="profile-image"
          />
          {isCurrentUser ? (
            <button
              className="edit-button"
              onClick={() => navigate(`/profile/${authorId}/edit`)}
            >
              Edit Profile
            </button>
          ) : (
            <FollowButton
              authorId={authorId}
              currentUserId={currentUserId}
              currentProfileData={authorCurrentData}
              profileData={authorProfileData}
            />
          )}
        </div>

        <div className="profile-details">
          <h1>{profileData.displayName}</h1>
          <div className="profile-stats">
            <div>
              <h2 style={{ cursor: 'pointer' }} onClick={handleFriendsClick}>
                {profileData.friends_count || 0}
              </h2>
              <p>Friends</p>
            </div>
            <div>
              <h2 style={{ cursor: 'pointer' }} onClick={handleFollowersClick}>
                {profileData.followers_count || 0}
              </h2>
              <p>Followers</p>
            </div>
            <div>
              <h2 style={{ cursor: 'pointer' }} onClick={handleFollowingClick}>
                {profileData.following_count || 0}
              </h2>
              <p>Following</p>
            </div>
          </div>

          {/* Profile Links */}
          <div className="profile-links">
            <div className="links-details">
              <p>
                GitHub Profile:{' '}
                {hasGithub ? (
                  <a
                    href={profileData.github}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {profileData.github.replace(/^https?:\/\/(www\.)?/i, '').replace(/\/$/, '')}
                  </a>
                ) : (
                  'Not linked'
                )}
              </p>
            </div>
            <div className="links-details">
              <button className="copy-profile-link" type="button" onClick={handleCopyProfileLink}>
                {linkCopied ? 'Link copied!' : 'Copy profile link'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="posts-section">
        {posts.length > 0 ? (
          posts.map((post) => (
            <PostBox
              key={post.id}
              post={post}
              poster={profileData}
            />
          ))
        ) : (
          <p>No posts available.</p>
        )}
      </div>

      {/* Authors List Modal for Followers, Friends, or Following */}
      {showModal && (
        <AuthorsListModal
          authors={modalData}
          onModalClose={closeModal}
          title={modalTitle}
        />
      )}
    </div>
  );
};

export default Profile;
