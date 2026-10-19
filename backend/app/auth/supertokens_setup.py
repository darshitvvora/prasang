"""SuperTokens initialisation: sessions (cookies for web, header tokens for mobile), phone OTP, optional Google."""
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.ingredients.smsdelivery.types import SMSDeliveryConfig, SMSDeliveryInterface
from supertokens_python.recipe import passwordless, session, thirdparty
from supertokens_python.recipe.passwordless import ContactPhoneOnlyConfig
from supertokens_python.recipe.passwordless.types import PasswordlessLoginSMSTemplateVars
from supertokens_python.recipe.thirdparty.provider import ProviderClientConfig, ProviderConfig, ProviderInput

from app.config import Settings

log = logging.getLogger(__name__)
AUTH_BASE_PATH = "/api/v1/auth"
SmsSender = Callable[[str, str], Awaitable[None]]
_initialised = False


async def log_sms(phone: str, text: str) -> None:
    """Local/dev SMS delivery: the OTP appears in the API logs."""
    log.warning("SMS to %s: %s", phone, text)


class _OtpSms(SMSDeliveryInterface[PasswordlessLoginSMSTemplateVars]):
    def __init__(self, send: SmsSender):
        self._send = send

    async def send_sms(self, template_vars: PasswordlessLoginSMSTemplateVars, user_context: dict[str, Any]) -> None:
        minutes = max(1, template_vars.code_life_time // 60000)
        await self._send(template_vars.phone_number,
                         f"{template_vars.user_input_code} is your Prasang login code. It expires in {minutes} minutes.")


def _client_ip(api_options) -> str:
    st_request = api_options.request
    forwarded = st_request.get_header("x-forwarded-for")  # set by our nginx in production
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    client = getattr(getattr(st_request, "request", None), "client", None)
    return (client.host if client else "unknown")[:64]


def _rate_limited_apis(original):
    """Refuse OTP sends over the per-phone / per-IP limits before SuperTokens creates (and texts) a code."""
    from supertokens_python.types.response import GeneralErrorResponse

    from app.auth.otp_limits import check_and_record
    from app.db import get_sessionmaker

    create_code_post = original.create_code_post
    resend_code_post = original.resend_code_post

    async def create_code(email, phone_number, session, should_try_linking_with_session_user, tenant_id, api_options, user_context):
        async with get_sessionmaker()() as db:
            problem = await check_and_record(db, phone_number or email or "", _client_ip(api_options))
        if problem:
            return GeneralErrorResponse(problem)
        return await create_code_post(email, phone_number, session, should_try_linking_with_session_user, tenant_id, api_options,
                                      user_context)

    async def resend_code(device_id, pre_auth_session_id, session, should_try_linking_with_session_user, tenant_id, api_options,
                          user_context):
        async with get_sessionmaker()() as db:
            problem = await check_and_record(db, f"device:{device_id}", _client_ip(api_options))
        if problem:
            return GeneralErrorResponse(problem)
        return await resend_code_post(device_id, pre_auth_session_id, session, should_try_linking_with_session_user, tenant_id,
                                      api_options, user_context)

    original.create_code_post = create_code
    original.resend_code_post = resend_code
    return original


def google_enabled(settings: Settings) -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def init_supertokens(settings: Settings, sms_sender: SmsSender = log_sms) -> None:
    global _initialised
    if _initialised:
        return
    recipes = [
        session.init(
            cookie_secure=settings.env == "production",
            cookie_same_site="lax",
            cookie_domain=settings.cookie_domain,
        ),
        passwordless.init(
            contact_config=ContactPhoneOnlyConfig(),
            flow_type="USER_INPUT_CODE",
            sms_delivery=SMSDeliveryConfig(service=_OtpSms(sms_sender)),
            override=passwordless.InputOverrideConfig(apis=_rate_limited_apis),
        ),
    ]
    if google_enabled(settings):
        recipes.append(thirdparty.init(sign_in_and_up_feature=thirdparty.SignInAndUpFeature(providers=[
            ProviderInput(config=ProviderConfig(third_party_id="google", clients=[
                ProviderClientConfig(client_id=settings.google_client_id, client_secret=settings.google_client_secret),
            ])),
        ])))
    init(
        app_info=InputAppInfo(
            app_name="Prasang",
            api_domain=settings.api_domain,
            website_domain=settings.website_domain,
            api_base_path=AUTH_BASE_PATH,
            website_base_path="/auth",
        ),
        supertokens_config=SupertokensConfig(connection_uri=settings.supertokens_uri, api_key=settings.supertokens_api_key),
        framework="fastapi",
        recipe_list=recipes,
        mode="asgi",
    )
    _initialised = True
