from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from posts.models import Comment, Like, Post
from users.models import Author, Follows
from .models import Notification


class NotificationTest(APITestCase):
    def setUp(self):
        def make_author(name):
            user = User.objects.create_user(username=name, password='somethingHardToCrack357')
            return Author.objects.create(user=user, display_name=name.title(), host='http://testserver')
        self.owner = make_author('owner')
        self.fan = make_author('fan')
        self.post = Post.objects.create(author_id=self.owner, title='Hello', content='c',
                                        content_type='text/plain', visibility='PUBLIC')

    def login_as(self, author):
        token = RefreshToken.for_user(author.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def like(self, author, obj):
        return Like.objects.create(author_id=author, object_id=obj.id, object_url=obj.url,
                                   content_type=ContentType.objects.get_for_model(obj))

    def verbs(self, author):
        return list(Notification.objects.filter(recipient=author).values_list('verb', flat=True))

    def test_like_through_the_api_notifies_the_post_author_and_unlike_removes_it(self):
        self.login_as(self.fan)
        like_url = f'/api/authors/{self.fan.id}/liked/'
        response = self.client.post(like_url, {'type': 'like', 'object': self.post.url}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.verbs(self.owner), [Notification.LIKE_POST])

        response = self.client.delete(f'{like_url}?object={self.post.url}')
        self.assertIn(response.status_code, (200, 204))
        self.assertEqual(self.verbs(self.owner), [])

    def test_comment_notifies_the_post_author_and_deleting_it_removes_it(self):
        comment = Comment.objects.create(author_id=self.fan, post_id=self.post, comment='nice')
        self.assertEqual(self.verbs(self.owner), [Notification.COMMENT])
        comment.delete()
        self.assertEqual(self.verbs(self.owner), [])

    def test_liking_a_comment_notifies_its_author(self):
        comment = Comment.objects.create(author_id=self.owner, post_id=self.post, comment='mine')
        self.like(self.fan, comment)
        notification = Notification.objects.get(recipient=self.owner)
        self.assertEqual(notification.verb, Notification.LIKE_COMMENT)
        self.assertEqual(notification.post, self.post)

    def test_no_notifications_for_your_own_actions(self):
        self.like(self.owner, self.post)
        Comment.objects.create(author_id=self.owner, post_id=self.post, comment='talking to myself')
        self.assertEqual(self.verbs(self.owner), [])

    def test_follow_request_accept_and_decline(self):
        follow = Follows.objects.create(local_follower_id=self.fan, followed_id=self.owner, status='PENDING')
        self.assertEqual(self.verbs(self.owner), [Notification.FOLLOW_REQUEST])

        # accepting through the API turns the request into "started following you" and tells the fan
        self.login_as(self.owner)
        response = self.client.put(f'/api/authors/{self.owner.id}/followers/{self.fan.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.verbs(self.owner), [Notification.FOLLOW])
        self.assertTrue(Notification.objects.get(recipient=self.owner).read)
        self.assertEqual(self.verbs(self.fan), [Notification.FOLLOW_ACCEPTED])

        # unfollowing removes both
        follow.delete()
        self.assertEqual(self.verbs(self.owner) + self.verbs(self.fan), [])

    def test_api_lists_only_your_notifications_and_marks_them_read(self):
        Comment.objects.create(author_id=self.fan, post_id=self.post, comment='first!')
        other_post = Post.objects.create(author_id=self.fan, title='Fan post', content='c', content_type='text/plain')
        self.like(self.owner, other_post)

        self.login_as(self.owner)
        data = self.client.get('/api/notifications/').data
        self.assertEqual(data['unread_count'], 1)
        [item] = data['notifications']
        self.assertEqual(item['verb'], Notification.COMMENT)
        self.assertEqual(item['actor']['displayName'], 'Fan')
        self.assertEqual(item['post']['title'], 'Hello')
        self.assertEqual(item['comment'], 'first!')
        self.assertFalse(item['read'])

        self.assertEqual(self.client.get('/api/notifications/unread_count/').data['unread_count'], 1)
        self.assertEqual(self.client.post('/api/notifications/read/').status_code, 204)
        self.assertEqual(self.client.get('/api/notifications/unread_count/').data['unread_count'], 0)
        # marking read only touched the owner's notifications
        self.assertFalse(Notification.objects.get(recipient=self.fan).read)

    def test_deleted_posts_drop_out_of_the_list(self):
        self.like(self.fan, self.post)
        self.post.visibility = 'DELETED'
        self.post.save()
        self.login_as(self.owner)
        data = self.client.get('/api/notifications/').data
        self.assertEqual((data['unread_count'], data['notifications']), (0, []))

    def test_requires_login(self):
        self.assertIn(self.client.get('/api/notifications/').status_code, (401, 403))

    def test_notifications_expire_after_30_days(self):
        old = Comment.objects.create(author_id=self.fan, post_id=self.post, comment='old')
        Comment.objects.create(author_id=self.fan, post_id=self.post, comment='new')
        Notification.objects.filter(comment=old).update(created=timezone.now() - timedelta(days=31))

        self.login_as(self.owner)
        data = self.client.get('/api/notifications/').data
        self.assertEqual([n['comment'] for n in data['notifications']], ['new'])
        self.assertEqual(data['unread_count'], 1)
        # expired ones are deleted, not just hidden
        self.assertFalse(Notification.objects.filter(comment=old).exists())

    def test_dismiss_removes_only_your_own_notifications(self):
        comment = Comment.objects.create(author_id=self.fan, post_id=self.post, comment='hi')
        theirs = Notification.objects.get(recipient=self.owner)
        mine_elsewhere = Post.objects.create(author_id=self.fan, title='p', content='c', content_type='text/plain')
        self.like(self.owner, mine_elsewhere)
        fans = Notification.objects.get(recipient=self.fan)

        self.login_as(self.owner)
        response = self.client.post('/api/notifications/dismiss/', {'ids': [str(theirs.id), str(fans.id)]}, format='json')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Notification.objects.filter(id=theirs.id).exists())
        self.assertTrue(Notification.objects.filter(id=fans.id).exists())
        # dismissing doesn't undo the comment itself
        self.assertTrue(Comment.objects.filter(id=comment.id).exists())

        for bad in ({}, {'ids': []}, {'ids': ['not-a-uuid']}):
            self.assertEqual(self.client.post('/api/notifications/dismiss/', bad, format='json').status_code, 400)
