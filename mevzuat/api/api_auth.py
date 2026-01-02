from ninja import Router, Schema
from django.contrib.auth import authenticate, login as django_login, logout as django_logout


router = Router()


class LoginSchema(Schema):
    username: str
    password: str


class UserSchema(Schema):
    username: str
    email: str = None
    first_name: str = None
    last_name: str = None


@router.post("/login")
def login(request, data: LoginSchema):
    user = authenticate(request, username=data.username, password=data.password)
    if user:
        django_login(request, user)
        return {"success": True, "user": {"username": user.username, "email": user.email}}
    return 401, {"success": False, "message": "Invalid credentials"}


@router.post("/logout")
def logout(request):
    django_logout(request)
    return {"success": True}


@router.get("/me", response={200: UserSchema, 401: None})
def me(request):
    if request.user.is_authenticated:
        return request.user
    return 401, None
