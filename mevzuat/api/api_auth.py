from typing import Optional
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.contrib.auth import (
    authenticate,
    login as django_login,
    logout as django_logout,
    get_user_model,
)
from django.core.mail import send_mail
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from ninja import Router, Schema
from ninja.params import Query
from sesame.utils import get_query_string


router = Router()


class LoginSchema(Schema):
    username: str
    password: str


class UserSchema(Schema):
    username: str
    email: str = None
    first_name: str = None
    last_name: str = None


class MagicLinkRequest(Schema):
    email: str
    redirect: Optional[str] = None


@router.post("/login")
def login(request, data: LoginSchema):
    user = authenticate(request, username=data.username, password=data.password)
    if user:
        django_login(request, user)
        return {"success": True, "user": {"username": user.username, "email": user.email}}
    return 401, {"success": False, "message": "Invalid credentials"}


def _allowed_redirect_hosts(request) -> set[str]:
    hosts = {request.get_host()}
    for candidate in (settings.FRONTEND_URL, settings.MAGIC_LINK_REDIRECT_URL):
        if candidate:
            host = urlparse(candidate).netloc
            if host:
                hosts.add(host)
    return hosts


def _resolve_redirect_url(request, redirect: Optional[str]) -> str:
    allowed_hosts = _allowed_redirect_hosts(request)
    if redirect and url_has_allowed_host_and_scheme(
        redirect,
        allowed_hosts=allowed_hosts,
        require_https=not settings.DEBUG,
    ):
        return redirect
    if settings.MAGIC_LINK_REDIRECT_URL:
        return settings.MAGIC_LINK_REDIRECT_URL
    if settings.FRONTEND_URL:
        return settings.FRONTEND_URL
    return request.build_absolute_uri("/")


@router.post("/magic-link")
def magic_link(request, data: MagicLinkRequest):
    email = data.email.strip().lower()
    if not email:
        return 400, {"success": False, "message": "Email is required"}

    User = get_user_model()
    user = (
        User.objects.filter(email__iexact=email).first()
        or User.objects.filter(username__iexact=email).first()
    )
    if not user:
        user = User.objects.create_user(username=email, email=email)

    confirm_url = request.build_absolute_uri("/api/auth/magic-link/confirm")
    query_string = get_query_string(user)
    redirect_url = _resolve_redirect_url(request, data.redirect)
    separator = "&" if "?" in query_string else "?"
    magic_link_url = f"{confirm_url}{query_string}{separator}{urlencode({'next': redirect_url})}"

    send_mail(
        "Your magic sign-in link",
        f"Click this link to sign in:\n\n{magic_link_url}",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=not settings.DEBUG,
    )

    response = {"success": True}
    if settings.DEBUG:
        response["link"] = magic_link_url
    return response


@router.get("/magic-link/confirm")
def magic_link_confirm(
    request,
    sesame: str = Query(...),
    next: Optional[str] = Query(None),
):
    user = authenticate(request, sesame=sesame)
    if not user:
        return HttpResponseBadRequest("Invalid or expired magic link.")

    django_login(request, user)
    redirect_url = _resolve_redirect_url(request, next)
    return HttpResponseRedirect(redirect_url)


@router.post("/logout")
def logout(request):
    django_logout(request)
    return {"success": True}


@router.get("/me", response={200: UserSchema, 401: None})
def me(request):
    if request.user.is_authenticated:
        return request.user
    return 401, None
