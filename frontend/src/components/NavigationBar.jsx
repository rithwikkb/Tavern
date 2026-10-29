import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  MenuOutlined,
  CottageOutlined,
  AddOutlined,
  PersonOutlined,
  NotificationsNoneOutlined,
  MeetingRoomOutlined,
} from '@mui/icons-material';
import '../styles/components/NavigationBar.css';
import Cookies from 'js-cookie';
import api from '../services/axios';
import { clearAuthCookies } from '../utils/authCookies';
import { getUnreadCount, NOTIFICATIONS_READ_EVENT } from '../services/NotificationsService';
import appLogo from  '../assets/NavLogo.png'

const NavigationBar = ({ expanded, onToggleExpanded }) => {
  //#region Variables
  const authorId = Cookies.get('author_id');
  const pages = [
    ['Home', <CottageOutlined fontSize="inherit" />, '/'],
    ['Post', <AddOutlined fontSize="inherit" />, '/post'],
    ['Notifications', <NotificationsNoneOutlined fontSize="inherit" />, '/notifications'],
    ['Profile', <PersonOutlined fontSize="inherit" />, `/profile/${authorId}`],
  ];
  const location = useLocation();
  // the server adds a trailing slash when a page is opened directly ("/notifications/")
  const currentPath = location.pathname.replace(/(.)\/$/, '$1');
  const [unreadCount, setUnreadCount] = useState(0);
  //#endregion

  // unread badge: refresh on every page change, every minute, and when the tab regains focus
  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const count = await getUnreadCount();
        if (!cancelled) {
          setUnreadCount(count);
        }
      } catch (error) {
        // a failed check just keeps the last count
      }
    };
    const clear = () => setUnreadCount(0);
    refresh();
    const intervalId = setInterval(refresh, 60000);
    window.addEventListener('focus', refresh);
    window.addEventListener(NOTIFICATIONS_READ_EVENT, clear);
    return () => {
      cancelled = true;
      clearInterval(intervalId);
      window.removeEventListener('focus', refresh);
      window.removeEventListener(NOTIFICATIONS_READ_EVENT, clear);
    };
  }, [location.pathname]);

  //#region Functions

  const handleToggle = () => {
    onToggleExpanded(!expanded); 
  };

  const navigate = useNavigate();

  const handleLogout = async () => {
    // revoke the refresh token on the server too, so a copied token stops working
    const refresh = Cookies.get('refresh_token');
    try {
      if (refresh) {
        await api.post('users/logout/', { refresh });
      }
    } catch (error) {
      console.error('Logout request failed:', error);
    } finally {
      clearAuthCookies();
      navigate('/login');
    }
  };
  //#endregion

  return (
    <nav className="navbar-menu" style={{ width: expanded ? 300 : 150 }}>
      {expanded && (
        <img
          src= { appLogo }
          alt="Tavern Logo"
          className="navbar-app-logo" 
        />
      )}
      <div className={`navbar-header${expanded ? '' : ' minimized'}`}>
        <div className="burger" onClick={handleToggle}>
          <div className="navbar-icon">
            <MenuOutlined fontSize="inherit" />
          </div>
        </div>
      </div>
      <ul className="navbar-list">
        {pages.map((page, index) => (
          <Link className="list-link" to={page[2]} key={index}>
            <li
              className={`navbar-list-item${currentPath === page[2] ? ' current' : ''}${expanded ? '' : ' minimized'}`}
              key={index}
            >
              <div className="navbar-icon">
                {page[1]}
                {page[2] === '/notifications' && unreadCount > 0 && (
                  <span className="navbar-badge" aria-label={`${unreadCount} unread`}>
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </div>
              {expanded && <span className="navbar-list-text">{page[0]}</span>}
            </li>
          </Link>
        ))}
      </ul>
      <div className="navbar-footer" onClick={handleLogout}>
        <div className="navbar-icon">
          <MeetingRoomOutlined fontSize="inherit" />
        </div>
        {expanded && <span className="navbar-list-text">Logout</span>}
      </div>
    </nav>
  );
};

export default NavigationBar;
