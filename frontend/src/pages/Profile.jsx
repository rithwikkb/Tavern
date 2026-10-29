import React, { useState, useEffect } from 'react';
import { getAuthorProfile } from '../services/profileService';
import { getAuthor } from '../services/AuthorsService';
import FollowButton from '../components/FollowButton';
import '../styles/pages/Profile.css';
import Cookies from 'js-cookie';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import PostBox from '../components/PostBox';
import { getFollowers } from '../services/FollowDetailService';
import { getFriends } from '../services/FriendsDetailService';
import { getFollowing } from '../services/FollowingDetailService';
import AuthorsListModal from '../components/AuthorsListModal';
import unknownUser from  '../assets/unknownUser.png';

const Profile = () => {
  const { authorId } = useParams();
  const currentUserId = Cookies.get('author_id');
  const [profileData, setProfileData] = useState(null);
  const [currentProfileData, setcurrentProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [modalData, setModalData] = useState([]);
  const [modalTitle, setModalTitle] = useState(''); // To display the title dynamically
  const [authorProfileData, setAuthorProfileData] = useState(null);
  const [authorCurrentData, setAuthorCurrentData] = useState(null);

  const [selectedFilter, setSelectedFilter] = useState('Public');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    getAuthorProfile(authorId)
      .then((data) => {
        setProfileData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [authorId]);
  
  useEffect(() => {
    getAuthor(authorId)
    .then((data) => {
      setAuthorProfileData(data);
      setLoading(false);
    })
    .catch((err) => {
      console.error(err);
      setLoading(false);
    });
  }, [authorId]);

  useEffect(() => {
    setShowModal(false);
  }, [location]);
  const closeModal = () => {
    setShowModal(false);
  };

  // Close the modal when the route changes
  useEffect(() => {
    getAuthorProfile(currentUserId)
      .then((data) => {
        setcurrentProfileData(data);
      })
      .catch((error) => {
        console.error(error);
      });
  }, []);

  useEffect(() => {
    getAuthor(currentUserId)
    .then((data) => {
      setAuthorCurrentData(data);
    })
    .catch((error) => {
      console.error(error);
    });
  }, []);

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
    return <p>Loading...</p>;
  }

  if (!profileData) {
    return <p>Error loading profile data.</p>;
  }

  const isCurrentUser = currentUserId === authorId;

  // new accounts default to the bare "https://github.com/" link
  const hasGithub = !!profileData.github && !/^https?:\/\/github\.com\/?$/.test(profileData.github);
  const publicPosts = profileData.public_posts || [];
  const friendsPosts = profileData.friends_posts || [];
  const unlistedPosts = profileData.unlisted_posts || [];
  const sharedPosts = profileData.shared_posts || [];
  const UnlistedAndSharesPosts = [...unlistedPosts, ...sharedPosts];

  const filteredPosts =
  selectedFilter === 'Public'
    ? profileData.public_posts || []
    : selectedFilter === 'Friends'
    ? profileData.friends_posts || []
    : [...(profileData.unlisted_posts || []), ...(profileData.shared_posts || [])];

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
                    {profileData.github}
                  </a>
                ) : (
                  'Not linked'
                )}
              </p>
            </div>
            <div className="links-details">
              <p>
                Profile Link:{' '}
                <a
                  href={`${new URL(profileData.host).origin}/profile/${profileData.id.endsWith('/') ? profileData.id.slice(0, -1).split('/').pop() : profileData.id.split('/').pop()}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {`${new URL(profileData.host).origin}/profile/${profileData.id.endsWith('/') ? profileData.id.slice(0, -1).split('/').pop() : profileData.id.split('/').pop()}`}
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="profile-filter-options">
        <h3
          onClick={() => setSelectedFilter('Public')}
          style={{
            opacity: selectedFilter === 'Public' ? '100%' : '50%',
            cursor: 'pointer',
          }}
        >
          Public
        </h3>
        <h3
          onClick={() => setSelectedFilter('Friends')}
          style={{
            opacity: selectedFilter === 'Friends' ? '100%' : '50%',
            cursor: 'pointer',
          }}
        >
          Friends
        </h3>
        <h3
          onClick={() => setSelectedFilter('Unlisted')}
          style={{
            opacity: selectedFilter === 'Unlisted' ? '100%' : '50%',
            cursor: 'pointer',
          }}
        >
          Unlisted
        </h3>
      </div>

      <div className="posts-section">
        {filteredPosts.length > 0 ? (
          filteredPosts.map((post) => (
            <PostBox
              key={post.id}
              post={post}
              poster={profileData}
              isUserEditable={isCurrentUser}
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
