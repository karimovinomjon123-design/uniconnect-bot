from aiogram import Router
from .start import router as start_router
from .subscription import router as subscription_router
from .referral import router as referral_router
from .leaderboard import router as leaderboard_router
from .profile import router as profile_router
from .info import router as info_router
from .admin import router as admin_router

def register_all_handlers(main_router: Router):
    """Barcha routerlarni asosiy dispatcherga ulash"""
    main_router.include_router(start_router)
    main_router.include_router(subscription_router)
    main_router.include_router(referral_router)
    main_router.include_router(leaderboard_router)
    main_router.include_router(profile_router)
    main_router.include_router(info_router)
    main_router.include_router(admin_router)
