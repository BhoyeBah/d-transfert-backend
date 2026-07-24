from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

# Stockage partagé (Redis) si REDIS_URL est configuré — nécessaire dès que plusieurs
# instances backend tournent derrière un load balancer, sinon chaque processus aurait son
# propre compteur et le rate limiting deviendrait inefficace. Sans REDIS_URL, repli sur un
# compteur en mémoire par processus (suffisant pour une seule instance, ex. développement).
limiter = Limiter(
    key_func=get_remote_address,
    enabled=True,
    storage_uri=get_settings().redis_url,
)
