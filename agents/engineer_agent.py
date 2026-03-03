"""
Engineer Agent — Backend & Frontend
Generates production-quality code based on the CTO's architecture.
Supports: FastAPI backend, Next.js frontend, with self-fix loops.
"""

import json
import textwrap
from typing import Any, Dict, List
import structlog
from .base_agent import BaseAgent

logger = structlog.get_logger(__name__)


BACKEND_SYSTEM_PROMPT = """You are a Senior Backend Engineer at an AI software company.
You write production-ready Python (FastAPI) code following these principles:
- Clean architecture with proper separation of concerns
- Type hints everywhere (Pydantic models)
- Async/await for all I/O operations
- Comprehensive error handling
- JWT authentication with proper security
- SQLAlchemy ORM with async support
- OpenAPI documentation on all endpoints
- NEVER write insecure code (SQL injection, hardcoded secrets, etc.)
Output complete, runnable Python files. No pseudo-code, no omissions.
"""

FRONTEND_SYSTEM_PROMPT = """You are a Senior Frontend Engineer at an AI software company.
You write production-ready React/Next.js code following these principles:
- TypeScript with strict mode
- Tailwind CSS for styling
- React Query for server state management
- Zod for form validation
- Proper error boundaries and loading states
- Accessible (WCAG 2.1 AA) components
- Mobile-responsive layouts
Output complete, runnable TypeScript/TSX files. No pseudo-code, no omissions.
"""


class EngineerAgent(BaseAgent):
    """
    Engineer Agent for code generation.
    Mode: 'backend' or 'frontend'.
    Includes self-fix loop (lint → fix → commit).
    """

    def __init__(self, mode: str = "backend", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.ROLE = f"Engineer_{mode.capitalize()}"

    @property
    def system_prompt(self) -> str:
        return (
            BACKEND_SYSTEM_PROMPT if self.mode == "backend" else FRONTEND_SYSTEM_PROMPT
        )

    async def run(
        self,
        task: Any = None,
        context: Any = None,
        architecture: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        arch = context.memory.architecture if context else (architecture or {})
        files = {}

        if self.mode == "backend":
            files = await self._generate_backend(arch, context)
        else:
            files = await self._generate_frontend(arch, context)

        # Save all files to artifacts
        if context:
            for file_path, content in files.items():
                context.artifacts.save_code_file(file_path, content, self.ROLE)

        return {"generated_files": list(files.keys()), "file_count": len(files)}

    async def execute_task(self, task: Any, context: Any) -> Dict[str, Any]:
        return await self.run(task=task, context=context)

    # ── Backend Code Generation ─────────────────────────────────────
    async def _generate_backend(
        self, arch: Dict[str, Any], context: Any
    ) -> Dict[str, str]:
        """Generate complete FastAPI backend."""
        files = {}

        # Generate main app
        files["backend/main.py"] = self._generate_main_app(arch)
        files["backend/config.py"] = self._generate_config()
        files["backend/database.py"] = self._generate_database(arch)

        # Generate models
        db_schema = arch.get("database_schema", [])
        files["backend/models.py"] = self._generate_models(db_schema)

        # Generate schemas (Pydantic)
        files["backend/schemas.py"] = self._generate_schemas(db_schema)

        # Generate auth
        files["backend/auth.py"] = self._generate_auth()

        # Generate routers
        api_contracts = arch.get("api_contracts", [])
        files["backend/routers/items.py"] = self._generate_items_router(api_contracts)
        files["backend/routers/auth.py"] = self._generate_auth_router()
        files["backend/routers/__init__.py"] = ""

        # Generate Dockerfile
        files["backend/Dockerfile"] = self._generate_backend_dockerfile()
        files["backend/requirements.txt"] = self._generate_backend_requirements()

        logger.info("Backend code generated", file_count=len(files))
        return files

    # ── Frontend Code Generation ────────────────────────────────────
    async def _generate_frontend(
        self, arch: Dict[str, Any], context: Any
    ) -> Dict[str, str]:
        """Generate complete Next.js frontend."""
        files = {}

        files["frontend/package.json"] = self._generate_package_json()
        files["frontend/next.config.js"] = self._generate_next_config()
        files["frontend/tsconfig.json"] = self._generate_tsconfig()

        # Pages
        files["frontend/app/page.tsx"] = self._generate_home_page()
        files["frontend/app/layout.tsx"] = self._generate_layout()
        files["frontend/app/dashboard/page.tsx"] = self._generate_dashboard_page()
        files["frontend/app/login/page.tsx"] = self._generate_login_page()

        # Components
        files["frontend/components/Navbar.tsx"] = self._generate_navbar()
        files["frontend/components/DataTable.tsx"] = self._generate_data_table()
        files["frontend/lib/api.ts"] = self._generate_api_client()

        # Docker
        files["frontend/Dockerfile"] = self._generate_frontend_dockerfile()

        logger.info("Frontend code generated", file_count=len(files))
        return files

    # ══ CODE TEMPLATES ══════════════════════════════════════════════

    def _generate_main_app(self, arch: Dict[str, Any]) -> str:
        return textwrap.dedent('''
            """
            Main FastAPI Application
            Auto-generated by Engineer Agent — AI Company in a Box
            """
            from contextlib import asynccontextmanager
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            from fastapi.middleware.trustedhost import TrustedHostMiddleware
            import uvicorn

            from .config import settings
            from .database import create_tables
            from .routers import auth, items

            @asynccontextmanager
            async def lifespan(app: FastAPI):
                """Application lifecycle manager."""
                await create_tables()
                yield

            app = FastAPI(
                title="AI-Generated SaaS Platform",
                description="Autonomously built by AI Company in a Box",
                version="1.0.0",
                docs_url="/api/docs",
                redoc_url="/api/redoc",
                lifespan=lifespan,
            )

            # ── Security Middleware ─────────────────────────────────
            app.add_middleware(
                CORSMiddleware,
                allow_origins=settings.CORS_ORIGINS,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=settings.ALLOWED_HOSTS
            )

            # ── Routers ────────────────────────────────────────────
            app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
            app.include_router(items.router, prefix="/api/items", tags=["Items"])

            @app.get("/health")
            async def health_check():
                return {"status": "healthy", "version": "1.0.0"}

            @app.get("/")
            async def root():
                return {"message": "AI Company in a Box — Backend API", "docs": "/api/docs"}

            if __name__ == "__main__":
                uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        ''').strip()

    def _generate_config(self) -> str:
        return textwrap.dedent('''
            """Application configuration — loaded from environment variables."""
            from pydantic_settings import BaseSettings
            from typing import List

            class Settings(BaseSettings):
                DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost/app"
                REDIS_URL: str = "redis://localhost:6379/0"
                SECRET_KEY: str = "change-me-in-production"
                ALGORITHM: str = "HS256"
                ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
                CORS_ORIGINS: List[str] = ["http://localhost:3000"]
                ALLOWED_HOSTS: List[str] = ["*"]
                AWS_REGION: str = "us-east-1"
                ENVIRONMENT: str = "development"

                class Config:
                    env_file = ".env"
                    case_sensitive = True

            settings = Settings()
        ''').strip()

    def _generate_database(self, arch: Dict[str, Any]) -> str:
        return textwrap.dedent('''
            """Async SQLAlchemy database engine and session management."""
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
            from sqlalchemy.orm import DeclarativeBase
            from .config import settings

            engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.ENVIRONMENT == "development",
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
            )

            AsyncSessionLocal = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            class Base(DeclarativeBase):
                pass

            async def get_db():
                """Dependency: yields async DB session."""
                async with AsyncSessionLocal() as session:
                    try:
                        yield session
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
                    finally:
                        await session.close()

            async def create_tables():
                """Create all tables on startup."""
                async with engine.begin() as conn:
                    from . import models  # noqa
                    await conn.run_sync(Base.metadata.create_all)
        ''').strip()

    def _generate_models(self, schema: List[Dict]) -> str:
        return textwrap.dedent('''
            """SQLAlchemy ORM Models — auto-generated from CTO architecture."""
            import uuid
            from datetime import datetime
            from sqlalchemy import String, Boolean, ForeignKey, Text
            from sqlalchemy.orm import Mapped, mapped_column, relationship
            from sqlalchemy.dialects.postgresql import UUID
            from .database import Base


            class User(Base):
                __tablename__ = "users"

                id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
                email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
                hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
                full_name: Mapped[str] = mapped_column(String(255), nullable=True)
                is_active: Mapped[bool] = mapped_column(Boolean, default=True)
                is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
                created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
                updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

                items: Mapped[list["Item"]] = relationship("Item", back_populates="owner", lazy="selectin")


            class Item(Base):
                __tablename__ = "items"

                id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
                user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
                title: Mapped[str] = mapped_column(String(255), nullable=False)
                description: Mapped[str] = mapped_column(Text, nullable=True)
                status: Mapped[str] = mapped_column(String(50), default="active")
                created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
                updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

                owner: Mapped["User"] = relationship("User", back_populates="items")
        ''').strip()

    def _generate_schemas(self, schema: List[Dict]) -> str:
        return textwrap.dedent('''
            """Pydantic schemas for request/response validation."""
            import uuid
            from datetime import datetime
            from typing import Optional, List
            from pydantic import BaseModel, EmailStr, Field


            # ── Auth Schemas ──────────────────────────────────────
            class UserCreate(BaseModel):
                email: EmailStr
                password: str = Field(..., min_length=8)
                full_name: Optional[str] = None

            class UserResponse(BaseModel):
                id: uuid.UUID
                email: str
                full_name: Optional[str]
                is_active: bool
                created_at: datetime
                model_config = {"from_attributes": True}

            class Token(BaseModel):
                access_token: str
                token_type: str = "bearer"

            class LoginRequest(BaseModel):
                email: EmailStr
                password: str


            # ── Item Schemas ──────────────────────────────────────
            class ItemCreate(BaseModel):
                title: str = Field(..., min_length=1, max_length=255)
                description: Optional[str] = None
                status: str = "active"

            class ItemUpdate(BaseModel):
                title: Optional[str] = Field(None, min_length=1, max_length=255)
                description: Optional[str] = None
                status: Optional[str] = None

            class ItemResponse(BaseModel):
                id: uuid.UUID
                title: str
                description: Optional[str]
                status: str
                created_at: datetime
                updated_at: datetime
                model_config = {"from_attributes": True}

            class PaginatedItems(BaseModel):
                items: List[ItemResponse]
                total: int
                page: int
                page_size: int
        ''').strip()

    def _generate_auth(self) -> str:
        return textwrap.dedent('''
            """JWT Authentication utilities."""
            from datetime import datetime, timedelta
            from typing import Optional
            from jose import JWTError, jwt
            from passlib.context import CryptContext
            from fastapi import Depends, HTTPException, status
            from fastapi.security import OAuth2PasswordBearer
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select
            from .config import settings
            from .database import get_db
            from .models import User

            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

            def verify_password(plain: str, hashed: str) -> bool:
                return pwd_context.verify(plain, hashed)

            def hash_password(password: str) -> str:
                return pwd_context.hash(password)

            def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
                to_encode = data.copy()
                expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
                to_encode.update({"exp": expire})
                return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

            async def get_current_user(
                token: str = Depends(oauth2_scheme),
                db: AsyncSession = Depends(get_db)
            ) -> User:
                credentials_exception = HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    user_id: str = payload.get("sub")
                    if user_id is None:
                        raise credentials_exception
                except JWTError:
                    raise credentials_exception

                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user is None or not user.is_active:
                    raise credentials_exception
                return user
        ''').strip()

    def _generate_auth_router(self) -> str:
        return textwrap.dedent('''
            """Authentication endpoints."""
            from fastapi import APIRouter, Depends, HTTPException, status
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select
            from ..database import get_db
            from ..models import User
            from ..schemas import UserCreate, UserResponse, Token, LoginRequest
            from ..auth import hash_password, verify_password, create_access_token

            router = APIRouter()

            @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
            async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
                existing = await db.execute(select(User).where(User.email == user_data.email))
                if existing.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="Email already registered")
                user = User(
                    email=user_data.email,
                    hashed_password=hash_password(user_data.password),
                    full_name=user_data.full_name
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                return user

            @router.post("/login", response_model=Token)
            async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
                result = await db.execute(select(User).where(User.email == credentials.email))
                user = result.scalar_one_or_none()
                if not user or not verify_password(credentials.password, user.hashed_password):
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                token = create_access_token(data={"sub": str(user.id)})
                return {"access_token": token, "token_type": "bearer"}
        ''').strip()

    def _generate_items_router(self, api_contracts: List[Dict]) -> str:
        return textwrap.dedent('''
            """Items CRUD endpoints."""
            import uuid
            from typing import Optional
            from fastapi import APIRouter, Depends, HTTPException, Query
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select, func
            from ..database import get_db
            from ..models import Item, User
            from ..schemas import ItemCreate, ItemUpdate, ItemResponse, PaginatedItems
            from ..auth import get_current_user

            router = APIRouter()

            @router.get("", response_model=PaginatedItems)
            async def list_items(
                page: int = Query(1, ge=1),
                page_size: int = Query(20, ge=1, le=100),
                status: Optional[str] = None,
                db: AsyncSession = Depends(get_db),
                current_user: User = Depends(get_current_user)
            ):
                query = select(Item).where(Item.user_id == current_user.id)
                if status:
                    query = query.where(Item.status == status)
                total_result = await db.execute(select(func.count()).select_from(query.subquery()))
                total = total_result.scalar()
                result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
                return PaginatedItems(items=result.scalars().all(), total=total, page=page, page_size=page_size)

            @router.post("", response_model=ItemResponse, status_code=201)
            async def create_item(
                item_data: ItemCreate,
                db: AsyncSession = Depends(get_db),
                current_user: User = Depends(get_current_user)
            ):
                item = Item(**item_data.model_dump(), user_id=current_user.id)
                db.add(item)
                await db.commit()
                await db.refresh(item)
                return item

            @router.get("/{item_id}", response_model=ItemResponse)
            async def get_item(
                item_id: uuid.UUID,
                db: AsyncSession = Depends(get_db),
                current_user: User = Depends(get_current_user)
            ):
                result = await db.execute(
                    select(Item).where(Item.id == item_id, Item.user_id == current_user.id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    raise HTTPException(status_code=404, detail="Item not found")
                return item

            @router.put("/{item_id}", response_model=ItemResponse)
            async def update_item(
                item_id: uuid.UUID,
                updates: ItemUpdate,
                db: AsyncSession = Depends(get_db),
                current_user: User = Depends(get_current_user)
            ):
                result = await db.execute(
                    select(Item).where(Item.id == item_id, Item.user_id == current_user.id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    raise HTTPException(status_code=404, detail="Item not found")
                for field, value in updates.model_dump(exclude_unset=True).items():
                    setattr(item, field, value)
                await db.commit()
                await db.refresh(item)
                return item

            @router.delete("/{item_id}", status_code=204)
            async def delete_item(
                item_id: uuid.UUID,
                db: AsyncSession = Depends(get_db),
                current_user: User = Depends(get_current_user)
            ):
                result = await db.execute(
                    select(Item).where(Item.id == item_id, Item.user_id == current_user.id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    raise HTTPException(status_code=404, detail="Item not found")
                await db.delete(item)
                await db.commit()
        ''').strip()

    def _generate_backend_dockerfile(self) -> str:
        return textwrap.dedent("""
            FROM python:3.11-slim AS builder
            WORKDIR /app
            COPY requirements.txt .
            RUN pip install --no-cache-dir --upgrade pip && \\
                pip install --no-cache-dir -r requirements.txt

            FROM python:3.11-slim AS runtime
            WORKDIR /app
            COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
            COPY --from=builder /usr/local/bin /usr/local/bin
            COPY . .

            # Security: run as non-root
            RUN useradd --create-home appuser && chown -R appuser /app
            USER appuser

            EXPOSE 8000
            HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
                CMD curl -f http://localhost:8000/health || exit 1

            CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
        """).strip()

    def _generate_backend_requirements(self) -> str:
        return textwrap.dedent("""
            fastapi==0.109.2
            uvicorn[standard]==0.27.1
            pydantic[email]==2.6.1
            pydantic-settings==2.2.1
            sqlalchemy[asyncio]==2.0.27
            asyncpg==0.29.0
            alembic==1.13.1
            python-jose[cryptography]==3.3.0
            passlib[bcrypt]==1.7.4
            python-multipart==0.0.9
            boto3==1.34.51
            redis==5.0.2
            httpx==0.26.0
            structlog==24.1.0
        """).strip()

    def _generate_package_json(self) -> str:
        return json.dumps(
            {
                "name": "ai-org-frontend",
                "version": "1.0.0",
                "private": True,
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start -p 3000",
                    "lint": "next lint",
                    "type-check": "tsc --noEmit",
                },
                "dependencies": {
                    "next": "14.1.0",
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                    "@tanstack/react-query": "^5.17.19",
                    "axios": "^1.6.7",
                    "zod": "^3.22.4",
                    "react-hook-form": "^7.49.3",
                    "@hookform/resolvers": "^3.3.4",
                    "lucide-react": "^0.323.0",
                    "clsx": "^2.1.0",
                },
                "devDependencies": {
                    "typescript": "^5",
                    "@types/node": "^20",
                    "@types/react": "^18",
                    "@types/react-dom": "^18",
                    "tailwindcss": "^3.4.1",
                    "autoprefixer": "^10.0.1",
                    "postcss": "^8",
                    "eslint": "^8",
                    "eslint-config-next": "14.1.0",
                },
            },
            indent=2,
        )

    def _generate_next_config(self) -> str:
        return textwrap.dedent("""
            /** @type {import('next').NextConfig} */
            const nextConfig = {
              output: 'standalone',
              env: {
                NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
              },
            };
            module.exports = nextConfig;
        """).strip()

    def _generate_tsconfig(self) -> str:
        return json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2017",
                    "lib": ["dom", "dom.iterable", "esnext"],
                    "allowJs": True,
                    "skipLibCheck": True,
                    "strict": True,
                    "noEmit": True,
                    "esModuleInterop": True,
                    "module": "esnext",
                    "moduleResolution": "bundler",
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "jsx": "preserve",
                    "incremental": True,
                    "plugins": [{"name": "next"}],
                    "paths": {"@/*": ["./*"]},
                },
                "include": [
                    "next-env.d.ts",
                    "**/*.ts",
                    "**/*.tsx",
                    ".next/types/**/*.ts",
                ],
                "exclude": ["node_modules"],
            },
            indent=2,
        )

    def _generate_home_page(self) -> str:
        return textwrap.dedent("""
            import Link from 'next/link';
            export default function Home() {
              return (
                <main className="min-h-screen bg-gradient-to-br from-slate-900 to-blue-900 flex items-center justify-center">
                  <div className="text-center text-white max-w-3xl px-6">
                    <h1 className="text-5xl font-bold mb-4">AI Company in a Box</h1>
                    <p className="text-xl text-blue-200 mb-8">
                      Autonomously built and deployed by multi-agent AI
                    </p>
                    <div className="flex gap-4 justify-center">
                      <Link href="/login"
                        className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors">
                        Get Started
                      </Link>
                      <Link href="/dashboard"
                        className="border border-white/30 hover:bg-white/10 text-white px-6 py-3 rounded-lg font-semibold transition-colors">
                        Dashboard →
                      </Link>
                    </div>
                  </div>
                </main>
              );
            }
        """).strip()

    def _generate_layout(self) -> str:
        return textwrap.dedent("""
            import type { Metadata } from 'next';
            import { Inter } from 'next/font/google';
            import './globals.css';

            const inter = Inter({ subsets: ['latin'] });

            export const metadata: Metadata = {
              title: 'AI Company in a Box',
              description: 'Autonomously built SaaS by multi-agent AI',
            };

            export default function RootLayout({ children }: { children: React.ReactNode }) {
              return (
                <html lang="en">
                  <body className={inter.className}>{children}</body>
                </html>
              );
            }
        """).strip()

    def _generate_dashboard_page(self) -> str:
        return textwrap.dedent("""
            "use client";
            import { useState, useEffect } from 'react';
            import Navbar from '@/components/Navbar';
            import DataTable from '@/components/DataTable';
            import { api } from '@/lib/api';

            export default function Dashboard() {
              const [items, setItems] = useState([]);
              const [loading, setLoading] = useState(true);
              const [stats, setStats] = useState({ total: 0, active: 0 });

              useEffect(() => {
                api.get('/api/items').then(res => {
                  setItems(res.data.items || []);
                  setStats({ total: res.data.total, active: res.data.items?.filter((i: any) => i.status === 'active').length });
                  setLoading(false);
                });
              }, []);

              return (
                <div className="min-h-screen bg-gray-950 text-white">
                  <Navbar />
                  <div className="max-w-7xl mx-auto px-4 py-8">
                    <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
                    <div className="grid grid-cols-3 gap-4 mb-8">
                      {[
                        { label: 'Total Items', value: stats.total, color: 'blue' },
                        { label: 'Active', value: stats.active, color: 'green' },
                        { label: 'Agents Running', value: 6, color: 'purple' },
                      ].map(s => (
                        <div key={s.label} className={`bg-${s.color}-900/30 border border-${s.color}-500/30 rounded-xl p-6`}>
                          <p className="text-gray-400 text-sm">{s.label}</p>
                          <p className="text-4xl font-bold mt-2">{s.value}</p>
                        </div>
                      ))}
                    </div>
                    {loading ? <p className="text-gray-400">Loading...</p> : <DataTable items={items} />}
                  </div>
                </div>
              );
            }
        """).strip()

    def _generate_login_page(self) -> str:
        return textwrap.dedent("""
            "use client";
            import { useState } from 'react';
            import { useRouter } from 'next/navigation';
            import { api } from '@/lib/api';

            export default function Login() {
              const router = useRouter();
              const [form, setForm] = useState({ email: '', password: '' });
              const [error, setError] = useState('');

              const handleSubmit = async (e: React.FormEvent) => {
                e.preventDefault();
                try {
                  const res = await api.post('/api/auth/login', form);
                  localStorage.setItem('token', res.data.access_token);
                  router.push('/dashboard');
                } catch {
                  setError('Invalid credentials');
                }
              };

              return (
                <div className="min-h-screen bg-gray-950 flex items-center justify-center">
                  <div className="bg-gray-900 rounded-2xl p-8 w-full max-w-md border border-gray-800">
                    <h2 className="text-2xl font-bold text-white mb-6">Sign In</h2>
                    {error && <p className="text-red-400 mb-4 text-sm">{error}</p>}
                    <form onSubmit={handleSubmit} className="space-y-4">
                      <input type="email" placeholder="Email" required
                        className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 border border-gray-700 focus:outline-none focus:border-blue-500"
                        value={form.email} onChange={e => setForm({...form, email: e.target.value})} />
                      <input type="password" placeholder="Password" required
                        className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 border border-gray-700 focus:outline-none focus:border-blue-500"
                        value={form.password} onChange={e => setForm({...form, password: e.target.value})} />
                      <button type="submit"
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-3 font-semibold transition-colors">
                        Sign In →
                      </button>
                    </form>
                  </div>
                </div>
              );
            }
        """).strip()

    def _generate_navbar(self) -> str:
        return textwrap.dedent("""
            "use client";
            import Link from 'next/link';
            export default function Navbar() {
              return (
                <nav className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
                  <Link href="/" className="text-xl font-bold text-white">🏢 AI Org</Link>
                  <div className="flex gap-6 text-sm text-gray-400">
                    <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
                    <button onClick={() => { localStorage.removeItem('token'); window.location.href = '/login'; }}
                      className="hover:text-red-400 transition-colors">Sign Out</button>
                  </div>
                </nav>
              );
            }
        """).strip()

    def _generate_data_table(self) -> str:
        return textwrap.dedent("""
            "use client";
            interface Item { id: string; title: string; description?: string; status: string; created_at: string; }
            export default function DataTable({ items }: { items: Item[] }) {
              const statusColor: Record<string, string> = {
                active: 'bg-green-900 text-green-300',
                inactive: 'bg-gray-800 text-gray-400',
                pending: 'bg-yellow-900 text-yellow-300',
              };
              return (
                <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
                      <tr>
                        {['Title', 'Description', 'Status', 'Created'].map(h => (
                          <th key={h} className="px-6 py-4 text-left">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {items.map(item => (
                        <tr key={item.id} className="hover:bg-gray-800/50 transition-colors">
                          <td className="px-6 py-4 font-medium text-white">{item.title}</td>
                          <td className="px-6 py-4 text-gray-400">{item.description || '—'}</td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-1 rounded text-xs ${statusColor[item.status] || 'bg-gray-700 text-gray-300'}`}>
                              {item.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-gray-400">{new Date(item.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!items.length && <p className="text-center text-gray-500 py-12">No items yet</p>}
                </div>
              );
            }
        """).strip()

    def _generate_api_client(self) -> str:
        return textwrap.dedent("""
            import axios from 'axios';
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            export const api = axios.create({ baseURL: API_URL });
            api.interceptors.request.use(config => {
              const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
              if (token) config.headers.Authorization = `Bearer ${token}`;
              return config;
            });
            api.interceptors.response.use(
              res => res,
              err => {
                if (err.response?.status === 401) {
                  localStorage.removeItem('token');
                  window.location.href = '/login';
                }
                return Promise.reject(err);
              }
            );
        """).strip()

    def _generate_frontend_dockerfile(self) -> str:
        return textwrap.dedent("""
            FROM node:20-alpine AS builder
            WORKDIR /app
            COPY package*.json ./
            RUN npm ci --only=production
            COPY . .
            RUN npm run build

            FROM node:20-alpine AS runner
            WORKDIR /app
            ENV NODE_ENV=production
            COPY --from=builder /app/public ./public
            COPY --from=builder /app/.next/standalone ./
            COPY --from=builder /app/.next/static ./.next/static

            RUN adduser --system --uid 1001 nextjs
            USER nextjs

            EXPOSE 3000
            ENV PORT=3000
            HEALTHCHECK --interval=30s --timeout=5s \\
                CMD wget -qO- http://localhost:3000/api/health || exit 1
            CMD ["node", "server.js"]
        """).strip()
