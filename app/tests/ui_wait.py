"""Wait for the MOD page's background scans and file operations in offscreen tests."""
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


def settle_mods(page, timeout=10):
    for _ in range(int(timeout * 100)):
        QApplication.processEvents()
        if page.idle:
            QApplication.processEvents()
            return page
        QTest.qWait(10)
    pytest.fail('MOD 页面后台任务未完成')


def refreshed(page):
    page.refresh()
    return settle_mods(page)
