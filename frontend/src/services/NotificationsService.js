import api from './axios';

// fired after notifications are marked read, so the badge in the nav updates right away
export const NOTIFICATIONS_READ_EVENT = 'tavern:notifications-read';

// URL: api/notifications/
export const getNotifications = async () => {
  const response = await api.get('notifications/');
  return response.data;
};

// URL: api/notifications/unread_count/
export const getUnreadCount = async () => {
  const response = await api.get('notifications/unread_count/');
  return response.data.unread_count;
};

// URL: api/notifications/read/
export const markAllNotificationsRead = async () => {
  await api.post('notifications/read/');
  window.dispatchEvent(new Event(NOTIFICATIONS_READ_EVENT));
};

// URL: api/notifications/dismiss/
export const dismissNotifications = async (ids) => {
  await api.post('notifications/dismiss/', { ids });
};
