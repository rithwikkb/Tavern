"""
The shared demo account and the small sample community around it.

`seed_all` (run by `manage.py seed_demo` on every deploy) creates or restores
everything. `maybe_reset_demo_account` runs when someone logs in as the demo
account: at most once every few minutes it undoes what earlier visitors did with
the demo account, so each new visitor starts from the same clean demo.

Every seeded object has a fixed id, so both are safe to run repeatedly.
"""
import base64
import io
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from posts.models import Comment, Like, Post
from users.models import Author, Follows


class DemoSeedError(Exception):
    """Raised instead of touching an account the seed didn't create."""


# Fixed namespace so seeded objects get the same ids on every run
SEED_NAMESPACE = uuid.UUID("5d1b7a2e-3c4f-4e8a-9b61-7f2c0d9e4a10")
DEFAULT_AVATAR = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"


def seed_id(*parts):
    return uuid.uuid5(SEED_NAMESPACE, "/".join(parts))


# username -> display name. The demo account is the one visitors log in as;
# the others exist only to make the feed feel alive and cannot log in.
PEOPLE = {
    settings.DEMO_USERNAME: "Demo Visitor",
    "sample_avery": "Avery Brooks",
    "sample_jordan": "Jordan Patel",
    "sample_sam": "Sam Rivera",
    "sample_taylor": "Taylor Kim",
    "sample_morgan": "Morgan Lee",
}

# (follower, followed, status)
FOLLOWS = [
    # demo and Avery follow each other, so they're friends and see each other's friends-only posts
    (settings.DEMO_USERNAME, "sample_avery", "ACCEPTED"),
    ("sample_avery", settings.DEMO_USERNAME, "ACCEPTED"),
    # demo follows Jordan, so Jordan's unlisted posts show up in the feed
    (settings.DEMO_USERNAME, "sample_jordan", "ACCEPTED"),
    ("sample_taylor", settings.DEMO_USERNAME, "ACCEPTED"),
    ("sample_morgan", "sample_avery", "ACCEPTED"),
    ("sample_avery", "sample_morgan", "ACCEPTED"),
    ("sample_jordan", "sample_sam", "ACCEPTED"),
    # a request waiting for the demo account to accept or deny
    ("sample_sam", settings.DEMO_USERNAME, "PENDING"),
]

# key, author, visibility, content type, title, content, hours ago
POSTS = [
    ("welcome", settings.DEMO_USERNAME, "PUBLIC", "text/markdown", "Welcome to Tavern 👋",
     "This is the **demo account** — feel free to look around!\n\n"
     "Things to try:\n\n"
     "- Like a post or leave a comment\n"
     "- Spot the **Public**, **Friends** and **Unlisted** badges on posts in your feed\n"
     "- Accept the waiting follow request in the top-right corner\n"
     "- Write your own post (plain text, Markdown, or an image)\n", 2),
    ("demo-thoughts", settings.DEMO_USERNAME, "FRIENDS", "text/plain", "Friends-only post",
     "Only my friends can see this one. Avery and I follow each other, so it shows up for both of us.", 30),
    ("hike", "sample_avery", "PUBLIC", "image/jpeg;base64", "Sunset from the ridge",
     None, 5),
    ("trail-notes", "sample_avery", "FRIENDS", "text/markdown", "Trail notes for next weekend",
     "Planning the next hike — friends only since it has the meeting spot.\n\n"
     "1. Meet at the trailhead at **7:00**\n"
     "2. Bring water and snacks\n"
     "3. Back by early afternoon", 9),
    ("bread", "sample_jordan", "PUBLIC", "text/plain", "Sourdough attempt #4",
     "Finally got a decent rise on this loaf. The trick was a longer cold proof overnight. "
     "Next goal: a more open crumb.", 12),
    ("recipe", "sample_jordan", "UNLISTED", "text/markdown", "My sourdough schedule",
     "Sharing this with followers who asked:\n\n"
     "| Step | Time |\n|---|---|\n| Feed starter | 9:00 |\n| Mix dough | 13:00 |\n"
     "| Stretch & fold | every 30 min ×4 |\n| Cold proof | overnight |\n| Bake | 8:00 |", 20),
    ("first-pr", "sample_sam", "PUBLIC", "text/markdown", "Merged my first open source PR",
     "Small fix to a docs typo, but it counts! If you're thinking about contributing somewhere, "
     "documentation is a great place to start.\n\n```bash\ngit checkout -b fix-typo\n```", 26),
    ("reading", "sample_taylor", "PUBLIC", "text/plain", "What I'm reading",
     "Halfway through a book on distributed systems. The chapter on consistency models finally made "
     "eventual consistency click for me.", 40),
    ("coffee", "sample_morgan", "PUBLIC", "text/plain", "New coffee spot",
     "Found a tiny café near campus with great pour-overs and plenty of outlets. "
     "Perfect for long study sessions.", 52),
]

# post key, commenter, text, hours ago
COMMENTS = [
    ("welcome", "sample_avery", "Welcome! Glad you're here.", 1),
    ("welcome", "sample_jordan", "Hi! Check out the sourdough post 🍞", 1),
    ("hike", "sample_jordan", "That view is unreal.", 4),
    ("hike", settings.DEMO_USERNAME, "Adding this trail to my list!", 3),
    ("bread", "sample_sam", "That crumb looks great already.", 11),
    ("bread", "sample_avery", "Save me a slice next time.", 10),
    ("first-pr", "sample_taylor", "Congrats! Docs fixes are underrated.", 25),
    ("trail-notes", settings.DEMO_USERNAME, "I'm in — see you at 7.", 8),
    ("coffee", "sample_jordan", "Need the name of this place.", 50),
]

# post key -> people who liked it
LIKES = {
    "welcome": ["sample_avery", "sample_jordan", "sample_taylor"],
    "hike": [settings.DEMO_USERNAME, "sample_jordan", "sample_sam", "sample_taylor", "sample_morgan"],
    "bread": ["sample_avery", "sample_sam", settings.DEMO_USERNAME],
    "first-pr": ["sample_taylor", "sample_jordan"],
    "reading": ["sample_morgan"],
    "coffee": ["sample_avery", "sample_taylor"],
    "trail-notes": [settings.DEMO_USERNAME],
}


def sunset_image_base64():
    """Draw a small sunset landscape so the demo includes an image post."""
    from PIL import Image, ImageDraw

    width, height = 900, 500
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    top, bottom = (255, 153, 102), (102, 51, 153)
    for y in range(height):
        t = y / height
        draw.line([(0, y), (width, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    draw.ellipse([560, 170, 720, 330], fill=(255, 214, 120))
    draw.polygon([(0, 500), (0, 340), (180, 230), (360, 360), (520, 260), (720, 380), (900, 290), (900, 500)],
                 fill=(46, 61, 52))
    draw.polygon([(0, 500), (0, 420), (250, 350), (480, 440), (700, 380), (900, 430), (900, 500)],
                 fill=(30, 40, 34))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82)
    return base64.b64encode(buffer.getvalue()).decode()


def avatar_url(site_url, username):
    """Each sample person has their own initials avatar, served from frontend/public/avatars/."""
    return f"{site_url}/avatars/{username}.svg"


def _upsert_follow(authors, follower, followed, follow_status):
    Follows.objects.update_or_create(
        id=seed_id("follow", follower, followed),
        defaults={
            "local_follower_id": authors[follower],
            "followed_id": authors[followed],
            "status": follow_status,
            "is_remote": False,
        },
    )


def _upsert_post(authors, key, author, visibility, content_type, title, content, hours_ago, now, image=None):
    post_id = seed_id("post", key)
    post = Post.objects.filter(id=post_id).first() or Post(id=post_id)
    post.author_id = authors[author]
    post.url = None
    post.title = title
    post.description = ""
    post.content_type = content_type
    post.content = (image or sunset_image_base64()) if content is None else content
    post.visibility = visibility
    post.save()
    # `published` is auto_now, so backdate it with an update to spread posts over time
    Post.objects.filter(id=post_id).update(published=now - timedelta(hours=hours_ago))
    return post


def _upsert_comment(authors, index, post, commenter, text, hours_ago, now):
    comment_id = seed_id("comment", post_key_of(post), str(index))
    comment = Comment.objects.filter(id=comment_id).first() or Comment(id=comment_id)
    comment.author_id = authors[commenter]
    comment.post_id = post
    comment.comment = text
    comment.content_type = "text/plain"
    comment.url = None
    comment.save()
    Comment.objects.filter(id=comment_id).update(published=now - timedelta(hours=hours_ago))


def _upsert_like(authors, post_key, post, liker):
    like_id = seed_id("like", post_key, liker)
    like = Like.objects.filter(id=like_id).first() or Like(id=like_id)
    like.author_id = authors[liker]
    like.content_type = ContentType.objects.get_for_model(Post)
    like.object_id = post.id
    like.object_url = f"{post.author_id.url.rstrip('/')}/posts/{post.id}"
    like.url = None
    like.save()


# seeded post id -> key, for comment ids (which include the post key)
_POST_KEYS = {}


def post_key_of(post):
    if not _POST_KEYS:
        _POST_KEYS.update({seed_id("post", key): key for key, *_ in POSTS})
    return _POST_KEYS[post.id]


@transaction.atomic
def seed_all(site_url):
    """Create or restore the demo account, the sample people and all their content."""
    site_url = site_url.rstrip("/")
    host = f"{site_url}/api/"
    now = timezone.now()

    authors = {}
    for username, display_name in PEOPLE.items():
        author_id = seed_id("author", username)
        existing = User.objects.filter(username=username).first()
        if existing is not None and not Author.objects.filter(user=existing, id=author_id).exists():
            # never take over an account a real person (or an admin) created with this username
            raise DemoSeedError(f"User '{username}' already exists and wasn't created by seed_demo; not touching it.")
        user, _ = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com"})
        if username == settings.DEMO_USERNAME:
            user.set_password(settings.DEMO_PASSWORD)
        else:
            user.set_unusable_password()  # sample people can't be logged into
        user.is_active = True
        user.save()

        author = Author.objects.filter(user=user).first() or Author(id=author_id, user=user)
        author.host = host
        # url/page are derived from host on save, so reset them in case the site URL changed
        author.url = None
        author.page = None
        author.display_name = display_name
        author.profile_image = avatar_url(site_url, username)
        author.github = ""
        author.save()
        authors[username] = author

    for follower, followed, follow_status in FOLLOWS:
        _upsert_follow(authors, follower, followed, follow_status)

    image = sunset_image_base64()
    posts = {}
    for key, *fields in POSTS:
        posts[key] = _upsert_post(authors, key, *fields, now=now, image=image)

    for index, (post_key, commenter, text, hours_ago) in enumerate(COMMENTS):
        _upsert_comment(authors, index, posts[post_key], commenter, text, hours_ago, now)

    for post_key, likers in LIKES.items():
        for liker in likers:
            _upsert_like(authors, post_key, posts[post_key], liker)


def reset_demo_account():
    """
    Undo what visitors did as the demo account: remove the demo's own posts, comments,
    likes and follows that aren't part of the seed, and put the seeded ones back
    (e.g. re-like posts it unliked, make Sam's follow request pending again).
    Content real users created stays untouched.
    """
    demo = settings.DEMO_USERNAME
    authors = {
        username: author
        for username, author in ((u, Author.objects.filter(id=seed_id("author", u)).first()) for u in PEOPLE)
        if author is not None
    }
    if demo not in authors:
        return  # demo data was never seeded
    demo_author = authors[demo]
    now = timezone.now()

    seeded_posts = {seed_id("post", key) for key, *_ in POSTS}
    seeded_comments = {seed_id("comment", post_key, str(i)) for i, (post_key, *_) in enumerate(COMMENTS)}
    seeded_likes = {seed_id("like", post_key, liker) for post_key, likers in LIKES.items() for liker in likers}
    seeded_follows = {seed_id("follow", follower, followed) for follower, followed, _ in FOLLOWS}

    with transaction.atomic():
        Post.objects.filter(author_id=demo_author).exclude(id__in=seeded_posts).delete()
        Comment.objects.filter(author_id=demo_author).exclude(id__in=seeded_comments).delete()
        Like.objects.filter(author_id=demo_author).exclude(id__in=seeded_likes).delete()
        (Follows.objects.filter(local_follower_id=demo_author) | Follows.objects.filter(followed_id=demo_author)) \
            .exclude(id__in=seeded_follows).delete()

        for follower, followed, follow_status in FOLLOWS:
            if demo in (follower, followed) and follower in authors and followed in authors:
                _upsert_follow(authors, follower, followed, follow_status)

        posts = {}
        for key, author, *fields in POSTS:
            existing = Post.objects.filter(id=seed_id("post", key)).first()
            if author == demo:
                posts[key] = _upsert_post(authors, key, author, *fields, now=now)
            elif existing is not None:
                posts[key] = existing

        for index, (post_key, commenter, text, hours_ago) in enumerate(COMMENTS):
            if commenter == demo and post_key in posts:
                _upsert_comment(authors, index, posts[post_key], commenter, text, hours_ago, now)

        for post_key, likers in LIKES.items():
            if demo in likers and post_key in posts:
                _upsert_like(authors, post_key, posts[post_key], demo)


def maybe_reset_demo_account(user):
    """
    Called when someone logs in as the demo account. Resets it unless that already
    happened in the last few minutes, so two visitors trying the demo at the same
    time don't wipe each other's changes. The demo user's `last_login` (unused
    otherwise, since logins issue JWTs) records when the last reset ran.
    """
    if user.username != settings.DEMO_USERNAME:
        return False
    now = timezone.now()
    with transaction.atomic():
        # lock the demo user's row so two simultaneous logins don't both reset
        demo_user = User.objects.select_for_update().get(pk=user.pk)
        interval = timedelta(minutes=settings.DEMO_RESET_INTERVAL_MINUTES)
        if demo_user.last_login and now - demo_user.last_login < interval:
            return False
        reset_demo_account()
        User.objects.filter(pk=user.pk).update(last_login=now)
    return True
