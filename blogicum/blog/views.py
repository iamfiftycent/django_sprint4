from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm, UserForm
from .models import Category, Comment, Post


User = get_user_model()
POSTS_PER_PAGE = 10


def published_posts():
    return Post.objects.filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True,
    )


def paginate_posts(request, posts):
    posts = posts.select_related('author', 'category', 'location').annotate(
        comment_count=Count(
            'comments', filter=Q(comments__is_published=True),
        ),
    ).order_by('-pub_date', '-pk')
    return Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get('page'))


def get_available_post(request, pk):
    posts = Post.objects.select_related('author', 'category', 'location')
    if request.user.is_authenticated:
        posts = posts.filter(
            Q(author=request.user) | Q(pk__in=published_posts()),
        )
    else:
        posts = posts.filter(pk__in=published_posts())
    return get_object_or_404(posts, pk=pk)


def render_post(request, post, form):
    return render(request, 'blog/detail.html', {
        'post': post,
        'form': form,
        'comments': post.comments.filter(
            is_published=True,
        ).select_related('author'),
    })


def index(request):
    return render(request, 'blog/index.html', {
        'page_obj': paginate_posts(request, published_posts()),
    })


def post_detail(request, pk):
    post = get_available_post(request, pk)
    return render_post(request, post, CommentForm())


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True,
    )
    return render(request, 'blog/category.html', {
        'page_obj': paginate_posts(
            request, published_posts().filter(category=category),
        ),
        'category': category,
    })


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    if request.user == profile_user:
        posts = Post.objects.all()
    else:
        posts = published_posts()
    return render(request, 'blog/profile.html', {
        'profile': profile_user,
        'page_obj': paginate_posts(request, posts.filter(author=profile_user)),
    })


@login_required
def edit_profile(request):
    form = UserForm(
        request.POST if request.method == 'POST' else None,
        instance=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        profile_user = form.save()
        return redirect('blog:profile', username=profile_user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:profile', username=post.author.username)
    else:
        form = PostForm()
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.author:
        return redirect('blog:post_detail', pk=post.pk)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.author:
        return redirect('blog:post_detail', pk=post.pk)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {
        'form': PostForm(instance=post),
    })


@login_required
@require_POST
def add_comment(request, pk):
    post = get_available_post(request, pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return redirect('blog:post_detail', pk=post.pk)
    return render_post(request, post, form)


@login_required
def edit_comment(request, pk, comment_id):
    post = get_available_post(request, pk)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if request.user != comment.author:
        return redirect('blog:post_detail', pk=post.pk)
    form = CommentForm(
        request.POST if request.method == 'POST' else None,
        instance=comment,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', pk=post.pk)
    return render(request, 'blog/comment.html', {
        'form': form, 'comment': comment,
    })


@login_required
def delete_comment(request, pk, comment_id):
    post = get_available_post(request, pk)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if request.user != comment.author:
        return redirect('blog:post_detail', pk=post.pk)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', pk=post.pk)
    return render(request, 'blog/comment.html', {'comment': comment})
