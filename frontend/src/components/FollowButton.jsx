import React, { useState, useEffect } from 'react';
import '../styles/components/FollowButton.css';
import {
  createFollowRequest,
  checkIfFollowing,
  rejectFollowRequest,
} from '../services/FollowService';

const FollowButton = ({
  authorId,
  currentUserId,
  currentProfileData,
  profileData,
}) => {
  const [buttonState, setButtonState] = useState('Follow');

  useEffect(() => {
    const checkFollowStatus = async () => {
      try {
        const response = await checkIfFollowing(authorId, currentUserId); // Checking if current user follows the profile's author

        if (response && response.status === 200) {
          //following accepted
          setButtonState('Unfollow'); //you're already following, so you can only unfollow from here
        } else if (response && response.status === 202) {
          //follow request pending
          //not following, so either requested, or hasn't requested
          setButtonState('Requested');
        } else {
          setButtonState('Follow');
        }
      } catch (error) {
        if (
          error.response &&
          error.response.data &&
          error.response.data.status === 'Follow request not found'
        ) {
          console.log('Follow request not found');
        } else {
          console.error('Error checking follow status:', error.message);
        }
      }
    };

    checkFollowStatus();
  }, [authorId, currentUserId]);

  const handleFollow = async () => {
    if (buttonState === 'Follow') {
      const followRequestData = {
        type: 'follow',
        summary: `${currentUserId} wants to follow ${authorId}`,
        actor: currentProfileData,
        object: profileData, //author you want to follow
      };

      console.log(followRequestData);

      try {
        const requestFollowResponse = await createFollowRequest(
          authorId,
          followRequestData
        );
        if (
          requestFollowResponse.status === 201 ||
          requestFollowResponse.status === 200
        ) {
          // Assuming 201 indicates a successful follow request
          setButtonState('Requested'); // Update button state after a successful follow request
        }
      } catch (error) {
        console.error(error);
      }
    }
  };

  const handleUnfollow = async () => {
    const name = profileData?.displayName || 'this person';
    if (buttonState === 'Unfollow' && window.confirm(`Unfollow ${name}?`)) {
      try {
        await rejectFollowRequest(authorId, currentUserId);
        setButtonState('Follow'); // Update button state after a successful unfollow request
      } catch (error) {
        console.error('Error unfollowing:', error);
      }
    }
  };

  const handleButtonClick = async () => {
    if (buttonState === 'Follow') {
      await handleFollow(); // Handle the follow action
    } else if (buttonState === 'Unfollow') {
      await handleUnfollow(); // Handle the unfollow action
    }
  };

  return (
    <button
      className={`follow-button ${buttonState === 'Requested' ? 'requested' : ''} ${buttonState === 'Unfollow' ? 'following' : ''}`}
      onClick={handleButtonClick}
      disabled={buttonState === 'Requested'}
    >
      {buttonState === 'Unfollow' ? (
        <>
          <span className="follow-button-idle">Following</span>
          <span className="follow-button-hover">Unfollow</span>
        </>
      ) : (
        buttonState
      )}
    </button>
  );
};

export default FollowButton;
