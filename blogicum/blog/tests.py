from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Comment, Post


User = get_user_model()


class BlogRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            'author', password='test-password',
        )
        cls.reader = User.objects.create_user(
            'reader', password='test-password',
        )
        cls.category = Category.objects.create(title='Категория', slug='topic')
        cls.post = Post.objects.create(
            title='Публикация', text='Текст публикации', author=cls.author,
            category=cls.category, pub_date=timezone.now() - timedelta(days=1),
        )
        cls.comment = Comment.objects.create(
            post=cls.post, author=cls.reader, text='Комментарий читателя',
        )

    def test_empty_profile_and_category_are_available(self):
        user = User.objects.create_user('имя.surname+tag@example.com')
        category = Category.objects.create(title='Пустая', slug='empty')
        urls = (
            reverse('blog:profile', args=[user.username]),
            reverse('blog:category_posts', args=[category.slug]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context['page_obj']), 0)

    def test_hidden_posts_are_private_in_profile_and_comment_endpoint(self):
        future = Post.objects.create(
            title='Отложенный', text='Текст', author=self.author,
            category=self.category,
            pub_date=timezone.now() + timedelta(days=1),
        )
        unpublished = Post.objects.create(
            title='Скрытый', text='Текст', author=self.author,
            category=self.category, is_published=False,
        )
        hidden_category = Category.objects.create(
            title='Скрытая', slug='hidden', is_published=False,
        )
        category_post = Post.objects.create(
            title='Скрытая категория', text='Текст', author=self.author,
            category=hidden_category,
        )
        profile_url = reverse('blog:profile', args=[self.author.username])
        for user in (None, self.reader):
            if user:
                self.client.force_login(user)
            response = self.client.get(profile_url)
            self.assertEqual(list(response.context['page_obj']), [self.post])
        for post in (future, unpublished, category_post):
            with self.subTest(post=post.title):
                response = self.client.post(
                    reverse('blog:add_comment', args=[post.pk]),
                    {'text': 'Попытка доступа'},
                )
                self.assertEqual(response.status_code, 404)
                self.assertFalse(post.comments.exists())
        self.client.force_login(self.author)
        response = self.client.get(profile_url)
        self.assertEqual(len(response.context['page_obj']), 4)

    def test_second_page_and_comment_count(self):
        for number in range(11):
            Post.objects.create(
                title=f'Публикация {number}', text='Текст', author=self.author,
                category=self.category,
            )
        Comment.objects.create(
            post=self.post, author=self.reader,
            text='Скрыт', is_published=False,
        )
        for url in (
            reverse('blog:index'),
            reverse('blog:profile', args=[self.author.username]),
            reverse('blog:category_posts', args=[self.category.slug]),
        ):
            with self.subTest(url=url):
                first = self.client.get(url).context['page_obj']
                second = self.client.get(url, {'page': 2}).context['page_obj']
                self.assertEqual(len(first), 10)
                self.assertEqual(len(second), 2)
                self.assertFalse(set(first) & set(second))
                self.assertEqual(second[-1].comment_count, 1)

    def test_create_scheduled_post_preserves_publication_date(self):
        self.client.force_login(self.author)
        scheduled = (timezone.now() + timedelta(days=1)).replace(
            second=0, microsecond=0,
        )
        response = self.client.post(reverse('blog:create_post'), {
            'title': 'Публикация в будущем', 'text': 'Текст',
            'category': self.category.pk,
            'pub_date': scheduled.strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertRedirects(
            response, reverse('blog:profile', args=[self.author.username]),
        )
        post = Post.objects.get(title='Публикация в будущем')
        self.assertEqual(post.pub_date, scheduled)
        url = reverse('blog:post_detail', args=[post.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_edit_profile_keeps_password_and_ignores_other_user_id(self):
        self.client.force_login(self.author)
        old_password = self.author.password
        response = self.client.post(reverse('blog:edit_profile'), {
            'id': self.reader.pk, 'username': 'new.name', 'first_name': 'Имя',
            'last_name': 'Фамилия', 'email': 'new@example.com',
            'password': 'plain-text', 'is_superuser': True,
        })
        self.assertRedirects(
            response, reverse('blog:profile', args=['new.name']),
        )
        self.author.refresh_from_db()
        self.reader.refresh_from_db()
        self.assertEqual(self.author.first_name, 'Имя')
        self.assertEqual(self.author.last_name, 'Фамилия')
        self.assertEqual(self.author.email, 'new@example.com')
        self.assertEqual(self.author.password, old_password)
        self.assertFalse(self.author.is_superuser)
        self.assertEqual(self.reader.username, 'reader')

    def test_comment_cannot_be_edited_or_deleted_under_another_post(self):
        other_post = Post.objects.create(
            title='Другая публикация', text='Текст', author=self.author,
            category=self.category,
        )
        self.client.force_login(self.reader)
        for name in ('blog:edit_comment', 'blog:delete_comment'):
            for method in ('get', 'post'):
                with self.subTest(name=name, method=method):
                    url = reverse(name, args=[other_post.pk, self.comment.pk])
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 404)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, 'Комментарий читателя')

    def test_delete_confirmation_does_not_delete_on_get(self):
        cases = (
            (self.author, 'blog:delete_post', [self.post.pk], self.post,
             self.post.title, 'blog/create.html'),
            (self.reader, 'blog:delete_comment',
             [self.post.pk, self.comment.pk], self.comment,
             self.comment.text, 'blog/comment.html'),
        )
        for user, name, args, item, text, template in cases:
            with self.subTest(name=name):
                self.client.force_login(user)
                response = self.client.get(reverse(name, args=args))
                self.assertContains(response, text)
                self.assertTemplateUsed(response, template)
                self.assertTrue(type(item).objects.filter(pk=item.pk).exists())

    def test_empty_edit_forms_show_validation_errors(self):
        for user, name, args, item in (
            (self.author, 'blog:edit_profile', [], self.author),
            (self.reader, 'blog:edit_comment',
             [self.post.pk, self.comment.pk], self.comment),
        ):
            with self.subTest(name=name):
                self.client.force_login(user)
                response = self.client.post(reverse(name, args=args), {})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].is_bound)
                self.assertTrue(response.context['form'].errors)
                item.refresh_from_db()
        self.assertEqual(self.author.username, 'author')
        self.assertEqual(self.comment.text, 'Комментарий читателя')
