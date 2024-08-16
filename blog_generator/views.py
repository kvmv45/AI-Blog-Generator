from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import os
import json
from pytube import YouTube
import assemblyai as aai
from openai import OpenAI
from .models import BlogPost

client = OpenAI(api_key="YOUR API KEY")


# Create your views here.
@login_required
def index(request):
    return render(request, "index.html")


@csrf_exempt
def generate_blog(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            yt_link = data["link"]
            # return JsonResponse({"content": yt_link})
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid data sent"}, status=400)

        # get youtube title
        title = yt_title(yt_link)

        # get transcription
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({"error": "Failed to get transcript"}, status=500)

        # use openAI to generate the blog
        # blog_content = generate_blog_from_transcription(transcription)
        # if not blog_content:
        #     return JsonResponse(
        #         {"error": "Failed to get generate blog article"}, status=500
        #     )

        # save blog article to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            content=transcription,
        )
        new_blog_article.save()

        # return blog article

        return JsonResponse({"content": transcription})
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title


def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    output_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(output_file)
    new_file = base + ".mp3"
    os.rename(output_file, new_file)
    return new_file


def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = "YOUR API KEY"

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    return transcript.text


def generate_blog_from_transcription(transcription):

    prompt = f"Based on the following transcript from the youtube video, write a comprehensive blog article, write it based on the transcript, but do not make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

    response = client.completions.create(model="davinci-002", prompt=prompt)
    # response = openai.Completion.create(
    #     model="text-davinci-003", prompt=prompt, max_tokens=1000
    # )

    # generated_content = response.choices[0].text.strip()
    generated_content = response["choices"][0]["text"]
    return generated_content


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/")
        else:
            error_message = "Invalid username or password"
            return render(request, "login.html", {"error_message": error_message})
    return render(request, "login.html")


def user_signup(request):
    if request.method == "POST":
        username = request.POST["name"]
        email = request.POST["email"]
        password = request.POST["password"]
        cpassword = request.POST["cpassword"]

        if password == cpassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect("/")
            except:
                error_message = "Error creating account, try again!"
        else:
            error_message = "Password does not match!"
            return render(request, "signup.html", {"error_message": error_message})
    return render(request, "signup.html")


def user_logout(request):
    logout(request)
    return redirect("/")


@login_required
def blog_list(request):
    articles = BlogPost.objects.filter(user=request.user)
    return render(request, "articles.html", {"articles": articles})


@login_required
def blog_details(request, pk):
    article = BlogPost.objects.get(id=pk)
    if article.user == request.user:
        return render(request, "single-blog.html", {"article": article})
    else:
        return redirect("/")
