from fastapi import APIRouter

from app.api.v1.endpoints import applications, auth, health, jobs, quota, resumes

router = APIRouter(prefix="/api/v1")

router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(applications.router, prefix="/applications", tags=["applications"])
router.include_router(quota.router, tags=["quota"])
