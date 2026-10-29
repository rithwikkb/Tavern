import { createPost, getAllPosts } from './PostsService';
import { getAuthorProfile } from './profileService';
import api from './axios';
import { getAuthor } from './AuthorsService';

// Only turn the newest few events into posts so one sync can't flood the feed
const MAX_NEW_ACTIVITY_POSTS = 5;

// Sync at most once per browser session per author, not on every visit to Home
const alreadySyncedThisSession = (authorId) => {
  try {
    return sessionStorage.getItem(`githubSynced:${authorId}`) === '1';
  } catch {
    return false;
  }
};

const markSyncedThisSession = (authorId) => {
  try {
    sessionStorage.setItem(`githubSynced:${authorId}`, '1');
  } catch {
    // storage unavailable (e.g. private mode); syncing again later is harmless
  }
};

export const makeGithubActivityPosts = async (authorId) => {
  if (alreadySyncedThisSession(authorId)) {
    return;
  }
  markSyncedThisSession(authorId);

  try {
    const author = await getAuthor(authorId);
    const authorProfile = await getAuthorProfile(authorId);
    const username = authorProfile.github?.replace(/\/+$/, '').split('/').pop();
    if (!username || username === 'github.com') {
      // no GitHub account linked
      return;
    }
    const posts = (await getAllPosts(authorId)).data.src ?? [];

    // 1. Get raw data from Github API (newest events first)
    const rawData = await getGithubActivityData(username);

    // 2. Parse date and event type, skipping events that already have a post
    const parsedData = rawData
      .map((event) => {
        return {
          id: event.id,
          date: new Date(event.created_at),
          type: event.type,
          repo: event.repo,
          payload: event.payload,
        };
      })
      .filter((event) => {
        return posts.every((post) => {
          return post.description !== String(event.id);
        });
      })
      .slice(0, MAX_NEW_ACTIVITY_POSTS);

    // 3. Turn into strings
    const stringifiedData = getStringsFromParsedData(parsedData, username);

    for (let i = 0; i < stringifiedData.length; i++) {
      const postData = new FormData();
      postData.append('author', author);
      postData.append('title', 'GitHub activity');
      postData.append('content', stringifiedData[i]);
      postData.append('contentType', 'text/plain');
      postData.append('visibility', 'PUBLIC');

      // add id to check if post already exists
      postData.append('description', String(parsedData[i].id));
      await createPost(authorId, postData);
    }
  } catch (error) {
    console.error(error);
  }
};

export const getGithubActivityData = async (username) => {
  try {
    const response = await api.get(`posts/github/events/${username}/`);
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error(error);
    return [];
  }
};

export const getStringsFromParsedData = (parsedData, username) => {

  const stringifiedData = parsedData.map((event) => {
    let stringifiedEvent = `On ${event.date.toDateString()}, ${username} `;

    const repoName = event.repo ? event.repo.name : 'a repository';

    switch (event.type) {
      case 'PushEvent':
        if (event.payload && event.payload.commits) {
          stringifiedEvent += `made ${event.payload.commits.length} commits in ${repoName}.`;
        } else {
          stringifiedEvent += `pushed to ${repoName}.`;
        }
        break;
      case 'PullRequestEvent':
        if (event.payload && event.payload.action) {
          stringifiedEvent += `${event.payload.action} a pull request in ${repoName}.`;
        } else {
          stringifiedEvent += `did something with a pull request in ${repoName}.`;
        }
        break;
      case 'IssuesEvent':
        if (event.payload && event.payload.action) {
          stringifiedEvent += `${event.payload.action} an issue in ${repoName}.`;
        } else {
          stringifiedEvent += `did something with an issue in ${repoName}.`;
        }
        break;
      case 'CreateEvent':
        stringifiedEvent += `created a branch or tag in ${repoName}.`;
        break;
      case 'ForkEvent':
        stringifiedEvent += `forked ${repoName}.`;
        break;
      case 'PublicEvent':
        stringifiedEvent += `made ${repoName} public.`;
        break;
      default:
        stringifiedEvent += `did something in Github.`;
        break;
    }
    return stringifiedEvent;
  });

  return stringifiedData;
};
