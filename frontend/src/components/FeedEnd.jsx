import React from 'react';
import PageLoader from './PageLoader';
import '../styles/components/FeedEnd.css';

// what goes under a scrolling list of posts: a spinner while the next page loads,
// a retry button if it failed, or "You're all caught up" at the very end
const FeedEnd = ({ feed }) => {
  if (feed.posts.length === 0) return null;
  return (
    <div className="feed-end">
      {feed.hasMore && <div ref={feed.sentinelRef} className="feed-end-sentinel" />}
      {feed.loadingMore ? (
        <PageLoader inline size={28} delay={0} />
      ) : feed.loadMoreFailed ? (
        <button type="button" className="feed-end-retry" onClick={feed.loadMore}>
          Couldn't load more posts. Try again
        </button>
      ) : (
        !feed.hasMore && <p className="feed-end-message">You're all caught up</p>
      )}
    </div>
  );
};

export default FeedEnd;
