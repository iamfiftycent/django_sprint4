from django.shortcuts import (
    render, get_list_or_404, get_object_or_404, redirect)
from datetime import datetime
from .models import Post, Category
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .forms import PostForm, UserForm


User = get_user_model()


def index(request):
    template_name = 'blog/index.html'
    now = datetime.now()
    post_list = Post.objects.all(
    ).filter(pub_date__lt=now,
             is_published=True,
             category__is_published=True
             ).order_by('-pub_date')[0:5]
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }

    return render(request, template_name, context)


def post_detail(request, pk):
    template_name = 'blog/detail.html'
    now = datetime.now()
    post = get_object_or_404(
        Post,
        pk=pk,
        pub_date__lt=now,
        is_published=True,
        category__is_published=True)

    context = {
        'post': post,
    }

    return render(request, template_name, context)


def category_posts(request, category_slug):
    template_name = 'blog/category.html'
    now = datetime.now()

    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True,
    )
    post_list = get_list_or_404(
        Post,
        pub_date__lt=now,
        is_published=True,
        category=category)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'category': category,
    }

    return render(request, template_name, context)


# функция отображения страницы пользователя
def profile(request, username):
    template_name = 'blog/profile.html'
    now = datetime.now()

    profile = get_object_or_404(
        User,
        username=username,
    )
    post_list = get_list_or_404(
        Post,
        pub_date__lt=now,
        author__username=username,
    )
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        'profile': profile,
        'page_obj': page_obj,
    }

    return render(request, template_name, context)


@login_required
def edit_profile(request, username):
    if request.user != username:
        return redirect('blog:profile', username=username)
    else:
        profile = get_object_or_404(
                User,
                username=username,
            )
        if request.method == 'POST':
            form = UserForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                return redirect('blog:profile', username=profile.username)
        else:
            form = UserForm(instance=profile)
        return render(request, 'user_edit.html', {'form': form})


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
        return redirect('blog:index')  # или другое перенаправление
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/edit.html', {'form': form})
