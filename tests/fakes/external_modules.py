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
