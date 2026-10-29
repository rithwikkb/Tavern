from django.contrib import admin
from .models import Post, Comment, Like

class PostAdmin(admin.ModelAdmin):
    #show url in django admin
    readonly_fields = ('url',)

class CommentAdmin(admin.ModelAdmin):
    #show url in django admin
    readonly_fields = ('url',)

class LikeAdmin(admin.ModelAdmin):
    #show url in django admin
    readonly_fields = ('url',)

# Register your models here.
admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Like, LikeAdmin)
