import { useCallback, useEffect, useRef, useState } from 'react';
import api from '../services/axios';

/**
 * Posts from a paged endpoint (`{ posts, next }`, newest first), loading the next page
 * when the returned `sentinelRef` element scrolls near the bottom of the screen.
 */
const useInfinitePosts = (url) => {
  const [posts, setPosts] = useState([]);
  const [next, setNext] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [loadMoreFailed, setLoadMoreFailed] = useState(false);
  // guards against loading the same page twice, and ignores answers for an old url
  const busy = useRef(false);
  const currentUrl = useRef(url);

  useEffect(() => {
    currentUrl.current = url;
    setPosts([]);
    setNext(null);
    setError(null);
    setLoadMoreFailed(false);
    setLoading(true);
    busy.current = true;
    api
      .get(url)
      .then((response) => {
        if (currentUrl.current !== url) return;
        setPosts(response.data.posts);
        setNext(response.data.next);
      })
      .catch((err) => {
        if (currentUrl.current === url) setError(err);
      })
      .finally(() => {
        if (currentUrl.current !== url) return;
        busy.current = false;
        setLoading(false);
      });
  }, [url]);

  const loadMore = useCallback(async () => {
    if (!next || busy.current) return;
    busy.current = true;
    setLoadingMore(true);
    setLoadMoreFailed(false);
    const requestedFor = url;
    try {
      const response = await api.get(url, { params: { before: next } });
      if (currentUrl.current !== requestedFor) return;
      // a post edited while scrolling can move; never show the same post twice
      setPosts((current) => {
        const seen = new Set(current.map((post) => post.id));
        return [...current, ...response.data.posts.filter((post) => !seen.has(post.id))];
      });
      setNext(response.data.next);
    } catch (err) {
      setLoadMoreFailed(true);
    } finally {
      busy.current = false;
      setLoadingMore(false);
    }
  }, [url, next]);

  // load the next page when the end of the list comes within ~600px of the screen
  const observer = useRef(null);
  const sentinelRef = useCallback(
    (node) => {
      if (observer.current) observer.current.disconnect();
      if (!node) return;
      observer.current = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) loadMore();
        },
        { rootMargin: '600px 0px' }
      );
      observer.current.observe(node);
    },
    [loadMore]
  );

  return { posts, loading, loadingMore, hasMore: Boolean(next), error, loadMoreFailed, loadMore, sentinelRef };
};

export default useInfinitePosts;
