"""Render the actual trait filter widgets offline with a temporary profile."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from core.settings import Settings
from ui.seedgen_page import SeedGenPage
from ui.seed_trait_dialog import SeedTraitDialog
from ui.theme import apply_theme

def main():
    output = ROOT/'build/review/seed-traits'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bbmod-trait-ui-') as temporary:
        os.environ['APPDATA'] = temporary
        app = QApplication([])
        apply_theme(app)
        settings = Settings()
        settings.set('seed_traits', {'required':['trait.huge','trait.iron_lungs'], 'excluded':['trait.clumsy'], 'match':'all'})
        context = SimpleNamespace(game=None, settings=settings)
        page = SeedGenPage(context)
        page.bro_count.setValue(1)
        page.resize(840, 590)
        page.show()
        app.processEvents()
        assert page.size().width() == 840 and page.size().height() == 590
        assert page.rect().contains(page.start_btn.mapTo(page, page.start_btn.rect().bottomRight()))
        assert page.rect().contains(page.traits_btn.mapTo(page, page.traits_btn.rect().bottomRight()))
        assert page.grab().save(str(output/'filters.png'))
        dialog = SeedTraitDialog(page.required_traits, page.excluded_traits, page.trait_match)
        dialog.resize(640, 520)
        dialog.show()
        app.processEvents()
        assert dialog.width() == 640 and dialog.height() == 520
        okay = dialog.buttons.button(QDialogButtonBox.Ok)
        assert dialog.rect().contains(okay.mapTo(dialog, okay.rect().bottomRight()))
        assert dialog.grab().save(str(output/'traits.png'))
        report = {'game_started':False,'filters':[page.width(),page.height()],
                  'dialog':[dialog.width(),dialog.height()],'traits':dialog.table.rowCount(),
                  'controls_in_bounds':True}
        (output/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))
        dialog.close()
        page.close()

if __name__ == '__main__':
    main()
