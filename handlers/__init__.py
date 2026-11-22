from aiogram import Router
from .start import router as start_router
from .subscription import router as subscription_router
from .referral import router as referral_router
from .stats import router as stats_router
from .leaderboard import router as leaderboard_router
from .prizes import router as prizes_router
from .rules import router as rules_router
from .status import router as status_router
from .profile import router as profile_router
from .info import router as info_router
from .admin import router as admin_router

def register_all_handlers(main_router: Router):
    """Barcha routerlarni tartib bilan dispatcherga ulash"""
    main_router.include_router(start_router)
    main_router.include_router(subscription_router)
    main_router.include_router(referral_router)
    main_router.include_router(stats_router)
    main_router.include_router(leaderboard_router)
    main_router.include_router(prizes_router)
    main_router.include_router(rules_router)
    main_router.include_router(status_router)
    main_router.include_router(profile_router)
    main_router.include_router(info_router)
    main_router.include_router(admin_router)
