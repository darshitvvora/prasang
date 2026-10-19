"""Import every ORM module so Base.metadata knows all tables (used by Alembic and tests)."""
from app.artists.models import ArtistDailyStat, ArtistProfile  # noqa: F401
from app.auth.models import OtpRequest, User  # noqa: F401
from app.leads.models import Lead  # noqa: F401
from app.locations.models import Locality  # noqa: F401
from app.media.models import ArtistMedia  # noqa: F401
from app.outbox.models import OutboxEvent  # noqa: F401
from app.reviews.models import Review  # noqa: F401
from app.site.models import ContactMessage  # noqa: F401
from app.subscriptions.models import PaymentEvent, Subscription, SubscriptionPlan  # noqa: F401
