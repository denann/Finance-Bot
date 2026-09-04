"""Install minimal optional dependency stubs before importing app modules."""

from __future__ import annotations

import sys
import types


def install_external_stubs() -> None:
    """Register import-only stubs without replacing already installed modules."""

    if "dotenv" not in sys.modules:
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *_args, **_kwargs: False
        sys.modules.setdefault("dotenv", dotenv)

    if "gspread" not in sys.modules:
        gspread = types.ModuleType("gspread")
        exceptions = types.ModuleType("gspread.exceptions")

        class WorksheetNotFound(Exception):
            """Stub missing-worksheet exception."""

        exceptions.WorksheetNotFound = WorksheetNotFound
        gspread.authorize = lambda *_args, **_kwargs: None
        gspread.exceptions = exceptions
        sys.modules.setdefault("gspread", gspread)
        sys.modules.setdefault("gspread.exceptions", exceptions)

    if "google.oauth2.service_account" not in sys.modules:
        google = sys.modules.setdefault("google", types.ModuleType("google"))
        oauth2 = sys.modules.setdefault("google.oauth2", types.ModuleType("google.oauth2"))
        service_account = types.ModuleType("google.oauth2.service_account")

        class Credentials:
            """Stub service-account factory used only during import."""

            @classmethod
            def from_service_account_file(cls, *_args, **_kwargs):
                return cls()

        service_account.Credentials = Credentials
        google.oauth2 = oauth2
        oauth2.service_account = service_account
        sys.modules.setdefault("google.oauth2.service_account", service_account)

    if "langchain_core.messages" not in sys.modules:
        langchain_core = sys.modules.setdefault("langchain_core", types.ModuleType("langchain_core"))
        messages = types.ModuleType("langchain_core.messages")

        class HumanMessage:
            """Store prompt content without creating a LangChain dependency."""

            def __init__(self, content=None, **_kwargs):
                self.content = content

        messages.HumanMessage = HumanMessage
        langchain_core.messages = messages
        sys.modules.setdefault("langchain_core.messages", messages)

    if "langchain_google_genai" not in sys.modules:
        langchain_google_genai = types.ModuleType("langchain_google_genai")

        class ChatGoogleGenerativeAI:
            """Fail closed if a test reaches the real Gemini client boundary."""

            def __init__(self, *_args, **_kwargs):
                raise RuntimeError("External Gemini client is disabled in offline tests.")

        langchain_google_genai.ChatGoogleGenerativeAI = ChatGoogleGenerativeAI
        sys.modules.setdefault("langchain_google_genai", langchain_google_genai)

    if "apscheduler.schedulers.asyncio" not in sys.modules:
        apscheduler = sys.modules.setdefault("apscheduler", types.ModuleType("apscheduler"))
        schedulers = sys.modules.setdefault("apscheduler.schedulers", types.ModuleType("apscheduler.schedulers"))
        asyncio_module = types.ModuleType("apscheduler.schedulers.asyncio")

        class AsyncIOScheduler:
            """Import-only scheduler stub for offline tests and benchmarks."""

            def __init__(self, *_args, **_kwargs):
                self.jobs = []

            def add_job(self, *args, **kwargs):
                self.jobs.append((args, kwargs))

            def start(self):
                return None

        asyncio_module.AsyncIOScheduler = AsyncIOScheduler
        schedulers.asyncio = asyncio_module
        apscheduler.schedulers = schedulers
        sys.modules.setdefault("apscheduler.schedulers.asyncio", asyncio_module)

    if "apscheduler.triggers.cron" not in sys.modules:
        apscheduler = sys.modules.setdefault("apscheduler", types.ModuleType("apscheduler"))
        triggers = sys.modules.setdefault("apscheduler.triggers", types.ModuleType("apscheduler.triggers"))
        cron_module = types.ModuleType("apscheduler.triggers.cron")

        class CronTrigger:
            """Store constructor arguments without scheduling real work."""

            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        cron_module.CronTrigger = CronTrigger
        triggers.cron = cron_module
        apscheduler.triggers = triggers
        sys.modules.setdefault("apscheduler.triggers.cron", cron_module)
