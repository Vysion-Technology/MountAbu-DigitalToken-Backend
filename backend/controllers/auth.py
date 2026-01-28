from fastapi.routing import APIRouter


router = APIRouter()


@router.post("/send-otp")
async def send_otp():
    pass


@router.post("/verify-otp")
async def verify_otp():
    pass


@router.post("/register")
async def register():
    pass


@router.post("/login")
async def login():
    pass


__all__ = ["router"]
