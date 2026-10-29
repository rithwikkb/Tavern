import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Cookies from 'js-cookie';
import { Close } from '@mui/icons-material';
import PageLoader from '../components/PageLoader';
import {
  dismissNotifications,
  getNotifications,
  markAllNotificationsRead,
} from '../services/NotificationsService';
import { fullDate, timeAgo } from '../utils/timeAgo';
import unknownUser from '../assets/unknownUser.png';
import '../styles/pages/Notifications.css';

const DAY = 24 * 60 * 60 * 1000;

// unread first, then older ones by age, like Instagram's notifications page
const sectionOf = (group) => {
  if (!group.read) return 'New';
  const age = Date.now() - new Date(group.created).getTime();
  if (age < DAY) return 'Today';
  if (age < 7 * DAY) return 'This week';
  return 'Earlier';
};
const SECTIONS = ['New', 'Today', 'This week', 'Earlier'];

// several likes on the same post (or comment), or several new followers, show as one row
const groupKey = (n) => {
  if (n.verb === 'like_post') return `like_post:${n.post?.id}`;
  if (n.verb === 'like_comment') return `like_comment:${n.commentId}`;
  if (n.verb === 'follow') return 'follow';
  return n.id;
};

const groupNotifications = (notifications) => {
  const groups = [];
  const byKey = {};
  notifications.forEach((n) => {
    // read and unread ones go in different sections, so never mix them in one row
    const key = `${n.read ? 'read' : 'unread'}:${groupKey(n)}`;
    const group = byKey[key];
    if (group) {
      group.ids.push(n.id);
      if (!group.actors.some((actor) => actor.id === n.actor.id)) {
        group.actors.push(n.actor);
      }
    } else {
      // the list arrives newest first, so the first one sets the group's time
      byKey[key] = { ...n, ids: [n.id], actors: [n.actor] };
      groups.push(byKey[key]);
    }
  });
  return groups;
};

// "Avery", "Avery and Jordan", "Avery, Jordan and 2 others"
const ActorNames = ({ actors }) => {
  const [first, second] = actors;
  if (actors.length === 1) return <strong>{first.displayName}</strong>;
  if (actors.length === 2) {
    return <><strong>{first.displayName}</strong> and <strong>{second.displayName}</strong></>;
  }
  const others = actors.length - 2;
  return (
    <>
      <strong>{first.displayName}</strong>, <strong>{second.displayName}</strong> and {others}{' '}
      {others === 1 ? 'other' : 'others'}
    </>
  );
};

// where clicking a notification takes you: the post it's about, or who followed you
const linkFor = (group) => {
  if (group.post) return `/post/${group.post.id}`;
  if (group.actors.length === 1) return `/profile/${group.actors[0].id}`;
  return `/profile/${Cookies.get('author_id')}`;
};

const Notifications = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getNotifications();
        // keep this visit's unread highlights, but clear the badge
        setNotifications(data.notifications);
        if (data.unread_count > 0) {
          markAllNotificationsRead().catch((err) => console.error(err));
        }
      } catch (err) {
        setError('Something went wrong loading your notifications.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleDismiss = async (group) => {
    try {
      await dismissNotifications(group.ids);
      setNotifications((current) => current.filter((n) => !group.ids.includes(n.id)));
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return <PageLoader />;
  }

  const groups = groupNotifications(notifications);
  const sections = SECTIONS.map((title) => ({
    title,
    groups: groups.filter((group) => sectionOf(group) === title),
  })).filter((section) => section.groups.length > 0);

  return (
    <div className="notifications-page">
      <h1>Notifications</h1>
      {error ? (
        <p className="notifications-message">{error}</p>
      ) : sections.length === 0 ? (
        <div className="notifications-card">
          <p className="notifications-message">
            Nothing yet. When someone likes or comments on your posts, or follows you, it'll show up here.
          </p>
        </div>
      ) : (
        sections.map((section) => (
          <section key={section.title} className="notifications-section">
            <h2 className="notifications-section-title">{section.title}</h2>
            <ul className="notifications-card">
              {section.groups.map((group) => (
                <li key={group.ids[0]} className={`notification-row${group.read ? '' : ' unread'}`}>
                  <Link to={linkFor(group)} className="notification-link">
                    <div className={`notification-avatars${group.actors.length > 1 ? ' stacked' : ''}`}>
                      {group.actors.slice(0, 2).map((actor) => (
                        <img
                          key={actor.id}
                          className="notification-avatar"
                          src={actor.profileImage || unknownUser}
                          alt=""
                          loading="lazy"
                        />
                      ))}
                    </div>
                    <div className="notification-body">
                      <p className="notification-text">
                        <ActorNames actors={group.actors} /> {group.text}
                        {group.post && group.verb !== 'like_comment' && (
                          <> <span className="notification-post-title">{group.post.title}</span></>
                        )}
                      </p>
                      {group.comment && (
                        <p className="notification-comment">“{group.comment}”</p>
                      )}
                      <span className="notification-time" title={fullDate(group.created)}>
                        {timeAgo(group.created)}
                      </span>
                    </div>
                    {!group.read && <span className="notification-dot" aria-label="New" />}
                  </Link>
                  <button
                    type="button"
                    className="notification-dismiss"
                    aria-label="Remove this notification"
                    title="Remove this notification"
                    onClick={() => handleDismiss(group)}
                  >
                    <Close fontSize="small" />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
};

export default Notifications;
