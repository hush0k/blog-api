from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), unique=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(_("name"), max_length=50)
    slug = models.SlugField(_("slug"), unique=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")

    id = models.AutoField(primary_key=True)
    author = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="posts"
    )
    title = models.CharField(_("title"), max_length=200)
    slug = models.SlugField(_("slug"), unique=True)
    body = models.TextField()
    category = models.ForeignKey(
        "Category", on_delete=models.SET_NULL, related_name="posts", null=True
    )
    tags = models.ManyToManyField("Tag", related_name="posts", blank=True)
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Comment(models.Model):
    id = models.AutoField(primary_key=True)
    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="comments"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Comment by %s on %s" % (self.author, self.post)
