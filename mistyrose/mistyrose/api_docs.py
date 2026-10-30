"""
The interactive API docs served at /swagger/.

drf-yasg can only guess at most of these views (they're plain APIViews that read
request.data by hand), so the docs are written out here instead: which endpoints are
shown, what each one does, what to send and what comes back. Endpoints that aren't
listed in ENDPOINTS (duplicate routes and leftovers from the class project's
federation spec) still work but are left out of the docs.
"""
import re

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator

API_DESCRIPTION = """
Tavern's REST API: the same API the web app uses.

**Logging in.** `POST /api/login/` with a username and password returns an
`access_token` (valid for an hour) and a `refresh_token`. Send the access token as
`Authorization: Bearer <access_token>`. To try authenticated endpoints here, log in
with the demo account (`demo` / `TavernDemo2026`), click **Authorize** and paste
`Bearer <access_token>`.

**IDs.** Authors, posts, comments and likes are identified by UUIDs. Responses also
include each object's full URL as its `id` (e.g.
`https://…/api/authors/<author id>/posts/<post id>`); the UUID is its last segment.

**Paging.** The feed and profile timelines return 20 posts at a time with a `next`
cursor; pass it back as `?before=<next>` for the following page. `next` is `null` on
the last page.

**Visibility.** Posts are `PUBLIC` (everyone), `FRIENDS` (the author and people who
follow each other with them), `UNLISTED` (anyone with the link; shown in the feed of
the author's followers) or `DELETED` (only the author). Endpoints never return posts,
comments or likes the requester isn't allowed to see.

Errors come back as JSON with an `error`, `message` or `detail` field.
""".strip()
# Swagger UI keeps single line breaks, so join each paragraph onto one line
API_DESCRIPTION = '\n\n'.join(' '.join(p.split('\n')) for p in API_DESCRIPTION.split('\n\n'))

# Swagger UI shows the groups in this order
TAGS = [
    ('Auth', 'Sign up, log in, refresh tokens and log out.'),
    ('Feed & posts', 'The home feed, profile timelines, and creating, editing and deleting posts.'),
    ('Comments', 'Reading, writing and deleting comments.'),
    ('Likes', 'Liking and unliking posts and comments, and listing likes.'),
    ('Follows', 'Follow requests, accepting and declining them, and unfollowing.'),
    ('Authors & profiles', 'Authors, profiles, and who follows whom.'),
    ('Notifications', "The logged-in author's notifications."),
]

# what each path parameter means, wherever it appears
PATH_PARAMS = {
    'author_serial': "The author's ID (UUID).",
    'author_id': "The author's ID (UUID).",
    'id': "The author's ID (UUID).",
    'follower_id': "The follower's author ID (UUID).",
    'post_serial': "The post's ID (UUID).",
    'post_id': "The post's ID (UUID).",
    'post_fqid': "The post's ID (UUID).",
    'comment_serial': "The comment's ID (UUID).",
    'comment_id': "The comment's ID (UUID).",
    'like_serial': "The like's ID (UUID).",
    'username': 'A GitHub username.',
}

# ---------- example objects ----------

HOST = 'https://tavern-weyv.onrender.com'
AUTHOR_ID = 'ec954a5d-08eb-5b89-b985-3b8fd81351d0'
POST_ID = '7b2f1c3e-5a4d-5e6f-8a9b-0c1d2e3f4a5b'

AUTHOR = {
    'type': 'author',
    'id': f'{HOST}/api/authors/{AUTHOR_ID}',
    'host': f'{HOST}/api/',
    'displayName': 'Avery Brooks',
    'github': 'https://github.com/averybrooks',
    'profileImage': f'{HOST}/avatars/sample_avery.svg',
    'page': f'{HOST}/api/profile/{AUTHOR_ID}/',
    'description': 'No Description',
}

LIKE = {
    'type': 'like',
    'id': f'{HOST}/api/authors/{AUTHOR_ID}/liked/0c4e…',
    'author': AUTHOR,
    'published': '2026-10-28T18:02:11Z',
    'object': f'{HOST}/api/authors/{AUTHOR_ID}/posts/{POST_ID}',
}

COMMENT = {
    'type': 'comment',
    'id': f'{HOST}/api/authors/{AUTHOR_ID}/commented/9d1a…',
    'author': AUTHOR,
    'comment': 'That view is unreal.',
    'contentType': 'text/plain',
    'published': '2026-10-28T18:05:40Z',
    'post': f'{HOST}/api/authors/{AUTHOR_ID}/posts/{POST_ID}',
    'likes': {'type': 'likes', 'count': 0, 'src': []},
}

POST = {
    'type': 'post',
    'id': f'{HOST}/api/authors/{AUTHOR_ID}/posts/{POST_ID}',
    'title': 'Trail notes for next weekend',
    'description': '',
    'contentType': 'text/markdown',
    'content': 'Planning the next hike — **friends only** since it has the meeting spot.',
    'visibility': 'FRIENDS',
    'published': '2026-10-28T14:30:00Z',
    'author': AUTHOR,
    'comments': [COMMENT],
    'likes': [LIKE],
    'likes_count': 1,
    'comments_count': 1,
    'liked_by_me': False,
}

FOLLOW_REQUEST = {
    'type': 'follow',
    'actor': {**AUTHOR, 'displayName': 'Sam Rivera'},
    'object': {**AUTHOR, 'displayName': 'Demo Visitor'},
}

NOTIFICATION = {
    'id': '295fc80b-63a0-471c-8287-57d7c3115153',
    'verb': 'comment',
    'text': 'commented on your post',
    'read': False,
    'created': '2026-10-28T18:05:40Z',
    'actor': {'id': AUTHOR_ID, 'displayName': 'Avery Brooks', 'profileImage': f'{HOST}/avatars/sample_avery.svg'},
    'post': {'id': POST_ID, 'title': 'Welcome to Tavern 👋'},
    'comment': "Welcome! Glad you're here.",
    'commentId': '9d1a5f60-…',
}

AUTHOR_LIST_ITEM = {k: AUTHOR[k] for k in ('type', 'id', 'host', 'displayName', 'page', 'github', 'profileImage')}

# ---------- helpers for writing endpoint specs ----------

S = openapi.Schema


def string(description, **kwargs):
    return S(type=openapi.TYPE_STRING, description=description, **kwargs)


def body(properties, required=(), example=None, description='Request body (JSON).'):
    return openapi.Parameter(
        'body', openapi.IN_BODY, description=description, required=True,
        schema=S(type=openapi.TYPE_OBJECT, properties=properties, required=list(required), example=example),
    )


def query(name, description, required=False, type=openapi.TYPE_STRING):
    return openapi.Parameter(name, openapi.IN_QUERY, description=description, required=required, type=type)


def respond(status, description, example=None):
    examples = {'application/json': example} if example is not None else None
    return str(status), openapi.Response(description, examples=examples)


NOT_LOGGED_IN = respond(401, 'Missing or expired access token.')
NOT_FOUND = respond(404, "Doesn't exist, or the requester isn't allowed to see it.")

POST_FIELDS = {
    'title': string('Post title.'),
    'description': string('Optional short description.'),
    'contentType': string(
        '`text/plain`, `text/markdown`, or an image type (`image/png;base64`, `image/jpeg;base64`, '
        '`image/gif;base64`) with base64 image data as the content.'
    ),
    'content': string('The post body: text, Markdown, or base64 image data.'),
    'visibility': string('`PUBLIC`, `FRIENDS` or `UNLISTED` (`DELETED` deletes the post).'),
}

PAGE = query('before', 'Cursor from the previous page\'s `next`, to load the following 20 posts.')
PAGED_POSTS = {'posts': [POST], 'next': '1761661800000000_7b2f1c3e-5a4d-5e6f-8a9b-0c1d2e3f4a5b'}

# ---------- the documented endpoints ----------
# (path, method) -> tag, summary, description, params, responses, public (no login needed)

ENDPOINTS = {
    # ----- Auth -----
    ('/api/signup/', 'post'): dict(
        tag='Auth', public=True,
        summary='Create an account',
        description='Creates a user and their author profile. Then log in with `POST /api/login/`. '
                    'Rate limited per IP.',
        params=[body(
            {'username': string('Letters, digits and @ . + - _'), 'email': string('A valid email address.'),
             'password': string("Must pass Django's password checks (length, not too common, …)."),
             'displayName': string('Name shown on posts.'), 'github': string('Optional GitHub profile URL.'),
             'profileImage': string('Optional profile picture URL (see the image upload endpoint).')},
            required=['username', 'email', 'password', 'displayName'],
            example={'username': 'avery', 'email': 'avery@example.com', 'password': 'a-long-passphrase',
                     'displayName': 'Avery Brooks'},
        )],
        responses=[respond(201, 'Account created; returns the new author.', AUTHOR),
                   respond(400, 'Missing or invalid field.', {'message': 'Enter a valid email address.'}),
                   respond(409, 'Username taken (or reserved).', {'message': 'Username already exists.'}),
                   respond(429, 'Too many signups from this IP; try again later.')],
    ),
    ('/api/login/', 'post'): dict(
        tag='Auth', public=True,
        summary='Log in',
        description='Returns JWT access and refresh tokens. Logging in as the demo account also resets '
                    'the demo (at most once every 10 minutes). Rate limited per IP.',
        params=[body({'username': string('Username.'), 'password': string('Password.')},
                     required=['username', 'password'],
                     example={'username': 'demo', 'password': 'TavernDemo2026'})],
        responses=[respond(200, 'Logged in.', {'author_id': '18e0d527-7aaa-59cb-a3a9-4c2e13522ca1',
                                               'access_token': 'eyJhbGciOi…', 'refresh_token': 'eyJhbGciOi…',
                                               'is_demo': True}),
                   respond(401, 'Wrong username or password.', {'error': 'Invalid username or password'}),
                   respond(429, 'Too many attempts; try again in a minute.')],
    ),
    ('/api/users/token/refresh/', 'post'): dict(
        tag='Auth', public=True,
        summary='Get a new access token',
        description='Trades a refresh token for a new access token. Refresh tokens are rotated: the response '
                    'includes a new refresh token, and the old one stops working.',
        params=[body({'refresh': string('The refresh token.')}, required=['refresh'],
                     example={'refresh': 'eyJhbGciOi…'})],
        responses=[respond(200, 'New tokens.', {'access': 'eyJhbGciOi…', 'refresh': 'eyJhbGciOi…'}),
                   respond(401, 'Refresh token is invalid, expired or already used.')],
    ),
    ('/api/users/logout/', 'post'): dict(
        tag='Auth', public=True,
        summary='Log out',
        description='Revokes the refresh token so it can no longer be used. Works even after the access '
                    'token has expired.',
        params=[body({'refresh': string('The refresh token to revoke.')}, required=['refresh'],
                     example={'refresh': 'eyJhbGciOi…'})],
        responses=[respond(200, 'Logged out.', {'message': 'Logged out successfully.'})],
    ),
    ('/authors/{username}/upload_image/', 'post'): dict(
        tag='Auth', public=True,
        summary='Upload a profile picture',
        description='Uploads an image (PNG, JPEG or GIF, up to 5 MB) and returns its URL, to use as '
                    '`profileImage` when signing up or editing a profile. Rate limited per IP.',
        consumes=['multipart/form-data'],
        params=[openapi.Parameter('username', openapi.IN_PATH, type=openapi.TYPE_STRING, required=True,
                                  description='The (new) username, used to name the upload.'),
                openapi.Parameter('profile_image', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True,
                                  description='The image file.')],
        responses=[respond(200, 'Uploaded.', {'message': 'Profile image uploaded successfully.',
                                              'url': 'https://i.imgur.com/abc123.png'}),
                   respond(400, 'No file, not an image, or too large.',
                           {'error': 'Profile picture must be 5 MB or smaller.'})],
    ),

    # ----- Feed & posts -----
    ('/api/posts/', 'get'): dict(
        tag='Feed & posts',
        summary='Home feed',
        description='Every post the logged-in author may see, newest first, 20 at a time: public posts from '
                    'everyone, unlisted posts from people they follow, friends-only posts from friends, '
                    'and all of their own posts.',
        params=[PAGE],
        responses=[respond(200, 'A page of posts and the cursor for the next one.', PAGED_POSTS),
                   respond(400, 'Invalid `before` cursor.'), NOT_LOGGED_IN],
    ),
    ('/api/authors/{author_serial}/timeline/', 'get'): dict(
        tag='Feed & posts',
        summary="An author's posts (profile timeline)",
        description="The author's posts newest first, 20 at a time. Friends-only posts are included only "
                    'for the author themselves and their friends; deleted posts never are.',
        params=[PAGE],
        responses=[respond(200, 'A page of posts and the cursor for the next one.', PAGED_POSTS),
                   respond(400, 'Invalid `before` cursor.'), NOT_FOUND],
    ),
    ('/api/authors/{author_serial}/posts/', 'post'): dict(
        tag='Feed & posts',
        summary='Create a post',
        description='Creates a post as the logged-in author (the path must be their own ID).',
        params=[body(POST_FIELDS, required=['title', 'contentType', 'content'],
                     example={'title': 'Sourdough attempt #5', 'contentType': 'text/markdown',
                              'content': 'Longer cold proof this time — **much** better crumb.',
                              'visibility': 'PUBLIC'})],
        responses=[respond(201, 'The new post.', POST), respond(400, 'Invalid field.'),
                   NOT_LOGGED_IN, respond(403, "Can't post as someone else.")],
    ),
    ('/api/authors/{author_serial}/posts/', 'get'): dict(
        tag='Feed & posts',
        summary="List an author's posts (all at once)",
        description="All of the author's posts the requester may see, in one response. The app uses the "
                    'paged `/timeline/` endpoint instead.',
        params=[],
        responses=[respond(200, 'The posts.', {'type': 'posts', 'page_number': 1, 'size': 1, 'count': 1,
                                               'src': ['…post…']})],
    ),
    ('/api/posts/{post_fqid}', 'get'): dict(
        tag='Feed & posts',
        summary='Get a post',
        description='A single post by its ID, in the same shape as feed posts. Unlisted posts work for '
                    'anyone with the link.',
        params=[],
        responses=[respond(200, 'The post.', POST), NOT_FOUND],
    ),
    ('/api/authors/{author_serial}/posts/{post_serial}/', 'get'): dict(
        tag='Feed & posts',
        summary='Get a post (by author and post ID)',
        description='A single post, looked up by its author and ID.',
        params=[],
        responses=[respond(200, 'The post.'), NOT_FOUND],
    ),
    ('/api/authors/{author_serial}/posts/{post_serial}/', 'put'): dict(
        tag='Feed & posts',
        summary='Edit or delete a post',
        description="Replaces the post's fields (send all of them). To delete a post, send it with "
                    '`visibility` set to `DELETED`; it disappears for everyone except its author. '
                    'Only the author can edit.',
        params=[body(POST_FIELDS, required=['title', 'contentType', 'content', 'visibility'],
                     example={'title': 'Sourdough attempt #5', 'contentType': 'text/plain',
                              'content': 'Edited: even better the next day.', 'visibility': 'PUBLIC'})],
        responses=[respond(200, 'The updated post.', POST), respond(400, 'Invalid field.'),
                   NOT_LOGGED_IN, respond(403, "Not the post's author."), respond(404, 'No such post.')],
    ),
    ('/api/authors/{author_serial}/posts/{post_serial}/image/', 'get'): dict(
        tag='Feed & posts',
        summary="Get an image post's image",
        description='The raw image of an image post (for use in an `<img>` tag).',
        produces=['image/png', 'image/jpeg', 'image/gif'],
        params=[],
        responses=[respond(200, 'The image file.'), NOT_FOUND],
    ),
    ('/api/posts/github/events/{username}/', 'get'): dict(
        tag='Feed & posts',
        summary="A GitHub user's recent public activity",
        description="Proxies GitHub's public events API (cached for 15 minutes, since GitHub limits "
                    'unauthenticated requests). The app turns these into posts for authors who linked '
                    'their GitHub.',
        params=[],
        responses=[respond(200, "GitHub's event objects (empty if GitHub can't be reached).",
                           [{'id': '43210987654', 'type': 'PushEvent', 'repo': {'name': 'averybrooks/trail-map'},
                             'created_at': '2026-10-28T16:20:00Z'}]),
                   respond(400, 'Not a valid GitHub username.')],
    ),

    # ----- Comments -----
    ('/api/authors/{author_serial}/posts/{post_serial}/comments/', 'get'): dict(
        tag='Comments',
        summary="A post's comments",
        description='All comments on the post, newest first.',
        params=[],
        responses=[respond(200, 'The comments.', {'type': 'comments', 'page_number': 1, 'size': 1, 'count': 1,
                                                  'src': [COMMENT]}),
                   NOT_FOUND],
    ),
    ('/api/authors/{author_serial}/commented/', 'post'): dict(
        tag='Comments',
        summary='Comment on a post',
        description='Adds a comment as the logged-in author (the path must be their own ID). '
                    "The post's author gets a notification.",
        params=[body({'type': string('Always `comment`.'), 'comment': string('The comment text.'),
                      'contentType': string('`text/plain` or `text/markdown`.'),
                      'post': string('The full URL of the post being commented on.')},
                     required=['type', 'comment', 'post'],
                     example={'type': 'comment', 'comment': 'That view is unreal.', 'contentType': 'text/plain',
                              'post': f'{HOST}/api/authors/{AUTHOR_ID}/posts/{POST_ID}'})],
        responses=[respond(201, 'The new comment.', COMMENT), respond(400, 'Missing or invalid field.'),
                   NOT_LOGGED_IN, respond(403, "Can't comment as someone else."),
                   respond(404, "The post doesn't exist or isn't visible.")],
    ),
    ('/api/authors/{author_serial}/commented/', 'get'): dict(
        tag='Comments',
        summary='Comments an author has made',
        description='Comments by the author, skipping ones on posts the requester can\'t see.',
        params=[],
        responses=[respond(200, 'The comments.', {'type': 'comments', 'page_number': 1, 'size': 1, 'count': 1,
                                                  'src': [COMMENT]})],
    ),
    ('/api/authors/{author_serial}/commented/{comment_serial}/', 'get'): dict(
        tag='Comments',
        summary='Get a comment',
        params=[],
        responses=[respond(200, 'The comment.', COMMENT), NOT_FOUND],
    ),
    ('/api/authors/{author_serial}/commented/{comment_serial}/', 'delete'): dict(
        tag='Comments',
        summary='Delete a comment',
        description='Allowed for whoever wrote the comment and for the author of the post it\'s on. '
                    '`author_serial` is the comment author\'s ID. Its likes and notifications go with it.',
        params=[],
        responses=[respond(204, 'Deleted.'), NOT_LOGGED_IN,
                   respond(403, "Neither the comment's author nor the post's author."),
                   respond(404, 'No such comment by that author.')],
    ),

    # ----- Likes -----
    ('/api/authors/{author_serial}/liked/', 'post'): dict(
        tag='Likes',
        summary='Like a post or comment',
        description='Likes the post or comment at `object` as the logged-in author (the path must be '
                    'their own ID). Liking something twice returns the existing like. The owner gets a '
                    'notification.',
        params=[body({'type': string('Always `like`.'),
                      'object': string('The full URL of the post or comment to like.')},
                     required=['type', 'object'],
                     example={'type': 'like', 'object': f'{HOST}/api/authors/{AUTHOR_ID}/posts/{POST_ID}'})],
        responses=[respond(201, 'Liked.', LIKE), respond(200, 'Already liked; the existing like.', LIKE),
                   respond(400, 'Missing or invalid `object`.'), NOT_LOGGED_IN,
                   respond(403, "Can't like as someone else."), NOT_FOUND],
    ),
    ('/api/authors/{author_serial}/liked/', 'delete'): dict(
        tag='Likes',
        summary='Unlike a post or comment',
        description="Removes the logged-in author's like from the post or comment at `object` "
                    '(given in the query string or the JSON body).',
        params=[query('object', 'The full URL of the liked post or comment.', required=True)],
        responses=[respond(204, 'Unliked.'), respond(400, '`object` is missing.'), NOT_LOGGED_IN,
                   respond(403, "Can't remove someone else's like."), respond(404, 'There was no like to remove.')],
    ),
    ('/api/authors/{author_serial}/liked/', 'get'): dict(
        tag='Likes',
        summary="Things an author has liked",
        description='Likes by the author, skipping ones on things the requester can\'t see.',
        params=[],
        responses=[respond(200, 'The likes.', {'type': 'likes', 'count': 1, 'src': [LIKE]})],
    ),
    ('/api/authors/{author_serial}/liked/{like_serial}/', 'get'): dict(
        tag='Likes',
        summary='Get a like',
        params=[],
        responses=[respond(200, 'The like.', LIKE), NOT_FOUND],
    ),
    ('/api/authors/{author_serial}/posts/{post_id}/likes/', 'get'): dict(
        tag='Likes',
        summary="A post's likes",
        description='Who liked the post, 10 per page, plus whether the requester has liked it.',
        params=[query('page', 'Page number (starts at 1).', type=openapi.TYPE_INTEGER),
                query('size', 'Likes per page (default 10, max 100).', type=openapi.TYPE_INTEGER)],
        responses=[respond(200, 'A page of likes.', {'type': 'likes', 'page_number': 1, 'size': 10, 'count': 1,
                                                     'liked_by_me': False, 'src': [LIKE]}),
                   NOT_FOUND],
    ),
    ('/api/authors/{author_id}/posts/{post_id}/comments/{comment_id}/likes/', 'get'): dict(
        tag='Likes',
        summary="A comment's likes",
        params=[],
        responses=[respond(200, 'The likes.', {'type': 'likes', 'count': 1, 'src': [LIKE]}), NOT_FOUND],
    ),

    # ----- Follows -----
    ('/api/authors/{author_id}/inbox/', 'post'): dict(
        tag='Follows',
        summary='Send a follow request',
        description='Asks to follow the author in the path. `actor` must be the logged-in author and '
                    '`object` the author being followed (only their `id` is needed). The request stays '
                    'pending until they accept it; they get a notification.',
        params=[body({'type': string('Always `follow`.'), 'summary': string('Optional text.'),
                      'actor': S(type=openapi.TYPE_OBJECT, description='The follower (you).',
                                 properties={'id': string("Your author URL or ID.")}),
                      'object': S(type=openapi.TYPE_OBJECT, description='The author to follow.',
                                  properties={'id': string("Their author URL or ID.")})},
                     required=['type', 'actor', 'object'],
                     example={'type': 'follow', 'actor': {'id': f'{HOST}/api/authors/<your id>'},
                              'object': {'id': f'{HOST}/api/authors/{AUTHOR_ID}'}})],
        responses=[respond(201, 'Request sent.', FOLLOW_REQUEST),
                   respond(200, 'Already requested or following; the existing follow.', FOLLOW_REQUEST),
                   respond(400, "Missing `actor`/`object`, or trying to follow yourself."),
                   NOT_LOGGED_IN, respond(403, "Can't send requests as someone else.")],
    ),
    ('/api/authors/{author_id}/inbox/follow_requests/', 'get'): dict(
        tag='Follows',
        summary='Pending follow requests',
        description='Follow requests waiting for the logged-in author to accept or decline.',
        params=[],
        responses=[respond(200, 'The pending requests.', [FOLLOW_REQUEST]), NOT_LOGGED_IN,
                   respond(403, "Not your requests.")],
    ),
    ('/api/authors/{author_id}/followers/{follower_id}/', 'get'): dict(
        tag='Follows',
        summary='Is this person following the author?',
        params=[],
        responses=[respond(200, 'Following.', {'status': 'Following'}),
                   respond(202, 'Requested, not accepted yet.', {'status': 'Follow request pending'}),
                   respond(404, 'Not following and no request.')],
    ),
    ('/api/authors/{author_id}/followers/{follower_id}/', 'put'): dict(
        tag='Follows',
        summary='Accept a follow request',
        description='The author in the path accepts the follower\'s pending request. The follower gets a '
                    'notification.',
        params=[],
        responses=[respond(200, 'Accepted.', {'status': 'Follow request accepted'}), NOT_LOGGED_IN,
                   respond(403, 'Only the author being followed can accept.'), respond(404, 'No such request.')],
    ),
    ('/api/authors/{author_id}/followers/{follower_id}/', 'delete'): dict(
        tag='Follows',
        summary='Decline a request or remove a follower',
        description='Declines a pending request or ends an existing follow. Either side may do this.',
        params=[],
        responses=[respond(204, 'Removed.'), NOT_LOGGED_IN, respond(403, 'Not part of this follow.'),
                   respond(404, 'No such follow.')],
    ),
    ('/api/authors/{author_id}/followers/{follower_id}/unfollow/', 'delete'): dict(
        tag='Follows',
        summary='Unfollow',
        description='The follower stops following the author in the path.',
        params=[],
        responses=[respond(200, 'Unfollowed.', {'message': 'Successfully unfollowed the author.'}),
                   NOT_LOGGED_IN, respond(403, 'Not part of this follow.'), respond(404, 'Not following.')],
    ),

    # ----- Authors & profiles -----
    ('/api/authors/', 'get'): dict(
        tag='Authors & profiles',
        summary='List authors (paged)',
        params=[query('page', 'Page number (starts at 1).', type=openapi.TYPE_INTEGER),
                query('size', 'Authors per page.', type=openapi.TYPE_INTEGER)],
        responses=[respond(200, 'A page of authors.', {'type': 'authors', 'authors': [AUTHOR]})],
    ),
    ('/api/authors/all/', 'get'): dict(
        tag='Authors & profiles',
        summary='List every author',
        description='Every author at once (used by the search bar).',
        params=[],
        responses=[respond(200, 'All authors.', [AUTHOR])],
    ),
    ('/api/authors/{id}/', 'get'): dict(
        tag='Authors & profiles',
        summary='Get an author',
        params=[],
        responses=[respond(200, 'The author.', AUTHOR), NOT_FOUND],
    ),
    ('/api/authors/{id}/profile/', 'get'): dict(
        tag='Authors & profiles',
        summary="An author's profile",
        description='The author plus their friend, follower and following counts. Their posts come from '
                    '`/api/authors/{id}/timeline/`.',
        params=[],
        responses=[respond(200, 'The profile.', {**AUTHOR, 'friends_count': 1, 'followers_count': 2,
                                                 'following_count': 2}),
                   NOT_FOUND],
    ),
    ('/api/authors/{id}/profile/edit/', 'get'): dict(
        tag='Authors & profiles',
        summary='Get editable profile fields',
        params=[],
        responses=[respond(200, 'The editable fields.', {'display_name': 'Avery Brooks',
                                                         'github': 'https://github.com/averybrooks',
                                                         'profile_image': f'{HOST}/avatars/sample_avery.svg'}),
                   NOT_FOUND],
    ),
    ('/api/authors/{id}/profile/edit/', 'put'): dict(
        tag='Authors & profiles',
        summary='Edit your profile',
        description="Updates the logged-in author's own profile. The shared demo account's profile "
                    "can't be changed.",
        params=[body({'display_name': string('Name shown on posts.'),
                      'github': string('GitHub profile URL (http/https).'),
                      'profile_image': string('Profile picture URL (http/https).')},
                     example={'display_name': 'Avery B.', 'github': 'https://github.com/averybrooks',
                              'profile_image': 'https://i.imgur.com/abc123.png'})],
        responses=[respond(200, 'The updated fields.'), respond(400, 'Invalid field (e.g. not a web URL).'),
                   NOT_LOGGED_IN, respond(403, "Not your profile, or the demo account.")],
    ),
    ('/api/authors/{id}/followers/', 'get'): dict(
        tag='Authors & profiles',
        summary="An author's followers",
        params=[],
        responses=[respond(200, 'Their followers.', {'type': 'followers', 'followers': [AUTHOR_LIST_ITEM]}),
                   NOT_FOUND],
    ),
    ('/api/authors/{id}/following/', 'get'): dict(
        tag='Authors & profiles',
        summary='Who an author follows',
        params=[],
        responses=[respond(200, 'Who they follow.', {'type': 'following', 'following': [AUTHOR_LIST_ITEM]}),
                   NOT_FOUND],
    ),
    ('/api/authors/{id}/friends/', 'get'): dict(
        tag='Authors & profiles',
        summary="An author's friends",
        description='People who follow the author and whom the author follows back.',
        params=[],
        responses=[respond(200, 'Their friends.', {'type': 'friends', 'friends': [AUTHOR_LIST_ITEM]}),
                   NOT_FOUND],
    ),

    # ----- Notifications -----
    ('/api/notifications/', 'get'): dict(
        tag='Notifications',
        summary='Your notifications',
        description='The logged-in author\'s 50 newest notifications from the last 30 days (older ones '
                    'expire) and how many are unread. `verb` is one of `like_post`, `like_comment`, '
                    '`comment`, `follow_request`, `follow`, `follow_accepted`.',
        params=[],
        responses=[respond(200, 'Notifications, newest first.', {'unread_count': 1, 'notifications': [NOTIFICATION]}),
                   NOT_LOGGED_IN],
    ),
    ('/api/notifications/unread_count/', 'get'): dict(
        tag='Notifications',
        summary='Unread notification count',
        description='Just the number of unread notifications (for a badge).',
        params=[],
        responses=[respond(200, 'The count.', {'unread_count': 3}), NOT_LOGGED_IN],
    ),
    ('/api/notifications/read/', 'post'): dict(
        tag='Notifications',
        summary='Mark all as read',
        params=[],
        responses=[respond(204, 'Done.'), NOT_LOGGED_IN],
    ),
    ('/api/notifications/dismiss/', 'post'): dict(
        tag='Notifications',
        summary='Dismiss notifications',
        description='Removes the given notifications from your list. The likes, comments or follows '
                    'themselves stay.',
        params=[body({'ids': S(type=openapi.TYPE_ARRAY, items=S(type=openapi.TYPE_STRING),
                               description='Notification IDs (up to 50).')},
                     required=['ids'], example={'ids': ['295fc80b-63a0-471c-8287-57d7c3115153']})],
        responses=[respond(204, 'Dismissed.'), respond(400, '`ids` missing, empty or invalid.'), NOT_LOGGED_IN],
    ),
}


class TavernSchemaGenerator(OpenAPISchemaGenerator):
    """Builds /swagger/ from ENDPOINTS instead of drf-yasg's guesses."""

    def should_include_endpoint(self, path, method, view, public):
        return (path, method.lower()) in ENDPOINTS

    def get_path_item(self, path, view_cls, operations):
        item = super().get_path_item(path, view_cls, operations)
        for param in item.get('parameters', []):
            param['description'] = PATH_PARAMS.get(param['name'], param.get('description', ''))
        return item

    def get_operation(self, view, path, prefix, method, components, request):
        operation = super().get_operation(view, path, prefix, method, components, request)
        spec = ENDPOINTS[(path, method.lower())]
        operation['tags'] = [spec['tag']]
        operation['summary'] = spec['summary']
        # a readable id from the summary, e.g. "Create a post" -> createAPost
        words = re.findall(r"[A-Za-z0-9]+", spec['summary'].replace("'", ''))
        operation['operationId'] = words[0].lower() + ''.join(w.capitalize() for w in words[1:])
        operation['description'] = spec.get('description', '')
        operation['parameters'] = spec['params']
        operation['responses'] = openapi.Responses(dict(spec['responses']))
        if 'consumes' in spec:
            operation['consumes'] = spec['consumes']
        if 'produces' in spec:
            operation['produces'] = spec['produces']
        if spec.get('public'):
            operation['security'] = []  # no token needed
        return operation

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema['tags'] = [{'name': name, 'description': description} for name, description in TAGS]
        return schema
