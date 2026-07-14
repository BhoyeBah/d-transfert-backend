from slowapi import Limiter
from slowapi.util import get_remote_address

# En mémoire, par processus : suffisant pour une seule instance backend. Si le
# déploiement passe un jour à plusieurs instances derrière un load balancer, ce compteur
# doit être déplacé vers un stockage partagé (Redis) pour rester efficace sur tous les
# nœuds — slowapi le supporte nativement via `storage_uri="redis://..."`.
limiter = Limiter(key_func=get_remote_address, enabled=True)
