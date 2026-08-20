import subprocess
import sys
import textwrap


def test_outer_sheets_boundary_reports_clean_rollback_vs_failed_rollback():
    script = textwrap.dedent(
        r'''
        import sys, types

        gspread = types.ModuleType("gspread")
        gspread.authorize = lambda *a, **k: None
        gspread_exceptions = types.ModuleType("gspread.exceptions")
        gspread_exceptions.WorksheetNotFound = type("WorksheetNotFound", (Exception,), {})
        gspread.exceptions = gspread_exceptions
        sys.modules["gspread"] = gspread
        sys.modules["gspread.exceptions"] = gspread_exceptions

        google = types.ModuleType("google")
        oauth2 = types.ModuleType("google.oauth2")
        sa = types.ModuleType("google.oauth2.service_account")
        class Credentials:
            @classmethod
            def from_service_account_info(cls, *a, **k):
                return cls()
        sa.Credentials = Credentials
        oauth2.service_account = sa
        google.oauth2 = oauth2
        sys.modules["google"] = google
        sys.modules["google.oauth2"] = oauth2
        sys.modules["google.oauth2.service_account"] = sa

        from app.sheets.client import sheets_transaction, SheetsAtomicWriteError
        from app.services.operation_errors import PartialMutationError

        rolled = []
        try:
            with sheets_transaction("clean") as tx:
                tx.add_rollback("first mutation", lambda: rolled.append("rolled"))
                raise PartialMutationError("second mutation failed", operation="split")
        except PartialMutationError:
            pass
        else:
            raise AssertionError("clean rollback swallowed the typed logical failure")
        assert rolled == ["rolled"]

        try:
            with sheets_transaction("uncertain") as tx:
                def broken_rollback():
                    raise RuntimeError("rollback unavailable")
                tx.add_rollback("first mutation", broken_rollback)
                raise PartialMutationError("second mutation failed", operation="split")
        except SheetsAtomicWriteError as exc:
            assert exc.rollback_ok is False
            assert any("rollback unavailable" in item for item in exc.rollback_errors)
        else:
            raise AssertionError("rollback uncertainty was reported as a clean cancellation")
        '''
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
