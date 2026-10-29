import "../styles/components/FollowRequests.css";
import { ExpandMore } from "@mui/icons-material";
import { Link } from 'react-router-dom';
import React, { useState, useEffect } from 'react';
import { transformFollowData } from "../utils/transformer";
import { getFollowRequests } from '../services/FollowService';
import { acceptFollowRequest, rejectFollowRequest } from '../services/FollowService';
import Cookies from 'js-cookie';
import unknownUser from  '../assets/followerUserUnknown.png';

const FollowRequests = () => {
    const [followRequests, setFollowRequests] = useState([]);
    const authorId = Cookies.get('author_id');
    const [isRequestsVisible, setIsRequestsVisible] = useState(true);

    const handleToggleRequests = () => {
        setIsRequestsVisible((prev) => !prev);
    };

    // Function to extract only the UUID from a full URL
    const extractUUID = (url) => {
        const match = url.match(/[0-9a-fA-F-]{36}/);  // Regex to find UUID
        return match ? match[0] : url;  // Return UUID if found, else return original URL
    };


    useEffect(() => {
        const fetchFollowRequests = async () => {
            // Fetch follow requests for the author
            try {
                const response = await getFollowRequests(authorId);
                setFollowRequests(transformFollowData(response));
            } catch (error) {
                console.error(error);
            }
        };

        fetchFollowRequests();
    }, [authorId]);

    const handleAccept = async (followerId) => {
        // Accept follow request
        try {
            const uuidFollowerId = extractUUID(followerId);  // Use only UUID
            await acceptFollowRequest(authorId, uuidFollowerId);
            setFollowRequests(prevRequests => prevRequests.filter(request => request.actor.id !== followerId));
        } catch (error) {
            console.error(error);
        }
    };

    const handleReject = async (followerId) => {
        // Deny follow request
        try {
            const uuidFollowerId = extractUUID(followerId);  // Use only UUID
            await rejectFollowRequest(authorId, uuidFollowerId);
            setFollowRequests(prevRequests => prevRequests.filter(request => request.actor.id !== followerId));
        } catch (error) {
            console.error(error);
        }
    };

    return (
        <section className="FollowRequest-container" aria-labelledby="follow-requests-title">
            <button
                type="button"
                className="requests-title"
                onClick={handleToggleRequests}
                aria-expanded={isRequestsVisible}
            >
                <span id="follow-requests-title">Follow requests</span>
                {followRequests.length > 0 && <span className="requests-count">{followRequests.length}</span>}
                <ExpandMore className={`requests-chevron ${isRequestsVisible ? '' : 'collapsed'}`} />
            </button>
            {isRequestsVisible && (
                followRequests.length === 0 ? (
                    <p className="requests-empty">No pending requests</p>
                ) : (
                    followRequests.map((followRequest) => (
                        <div key={followRequest.actor.id} className="follow-request-box">
                            <Link
                                className="follower-picAndName"
                                to={`/profile/${followRequest.actor.id.replace(/\/$/, '').split('/').pop()}`}
                            >
                                <img
                                    className="follower-profilePic"
                                    src={followRequest.actor.profileImage || unknownUser}
                                    alt=""
                                />
                                <div className="follower-text">
                                    <div className="follower-name">{followRequest.actor.displayName}</div>
                                    <div className="follower-subtitle">wants to follow you</div>
                                </div>
                            </Link>
                            <div className="btns">
                                <button className="accept-button" onClick={() => handleAccept(followRequest.actor.id)}>
                                    Accept
                                </button>
                                <button className="reject-button" onClick={() => handleReject(followRequest.actor.id)}>
                                    Decline
                                </button>
                            </div>
                        </div>
                    ))
                )
            )}
        </section>
    );
};

export default FollowRequests;
