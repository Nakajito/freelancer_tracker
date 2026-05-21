from django.conf import settings


def demo_mode(request: object) -> dict:
    is_demo = (
        hasattr(request, "user")
        and request.user.is_authenticated
        and request.user.email == settings.DEMO_USER_EMAIL
    )
    return {"is_demo": is_demo}
