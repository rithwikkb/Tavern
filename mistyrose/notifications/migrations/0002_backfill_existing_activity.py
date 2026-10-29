from django.db import migrations


def backfill(apps, schema_editor):
    """
    Create notifications for likes, comments and follows that existed before
    notifications did. They're marked read so nobody's bell lights up with old activity
    (the demo account's become unread again on its next reset).
    """
    Notification = apps.get_model('notifications', 'Notification')
    Like = apps.get_model('posts', 'Like')
    Comment = apps.get_model('posts', 'Comment')
    Post = apps.get_model('posts', 'Post')
    Follows = apps.get_model('users', 'Follows')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    def add(recipient_id, actor_id, verb, **source):
        if recipient_id and actor_id and recipient_id != actor_id:
            Notification.objects.get_or_create(
                recipient_id=recipient_id, actor_id=actor_id, verb=verb, defaults={'read': True}, **source
            )

    post_type = ContentType.objects.filter(app_label='posts', model='post').first()
    comment_type = ContentType.objects.filter(app_label='posts', model='comment').first()

    for like in Like.objects.all():
        if post_type and like.content_type_id == post_type.id:
            post = Post.objects.filter(id=like.object_id).first()
            if post:
                add(post.author_id_id, like.author_id_id, 'like_post', like=like, post=post)
        elif comment_type and like.content_type_id == comment_type.id:
            comment = Comment.objects.filter(id=like.object_id).select_related('post_id').first()
            if comment:
                add(comment.author_id_id, like.author_id_id, 'like_comment',
                    like=like, comment=comment, post=comment.post_id)

    for comment in Comment.objects.select_related('post_id'):
        add(comment.post_id.author_id_id, comment.author_id_id, 'comment', comment=comment, post=comment.post_id)

    for follow in Follows.objects.exclude(local_follower_id=None):
        verb = 'follow_request' if follow.status == 'PENDING' else 'follow'
        add(follow.followed_id_id, follow.local_follower_id_id, verb, follow=follow)


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
