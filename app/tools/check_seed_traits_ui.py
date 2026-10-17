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
from core.seedgen.log_watcher import SeedResult
from ui.seedgen_page import SeedGenPage
from ui.seed_trait_dialog import SeedTraitDialog
from ui.seed_star_dialog import SeedStarDialog
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
        dialog.search.setText('毅然')
        app.processEvents()
        assert dialog.grab().save(str(output/'determined.png'))
        stars = SeedStarDialog(9, 9, {'MeleeSkill': (3,3), 'MeleeDefense': (3,3), 'Stamina': (3,3)})
        stars.show()
        app.processEvents()
        assert stars.selection() == (9, 9, {'Stamina': (3,3), 'MeleeSkill': (3,3), 'MeleeDefense': (3,3)})
        assert stars.rect().contains(stars.buttons.mapTo(stars, stars.buttons.rect().bottomRight()))
        assert stars.grab().save(str(output/'stars.png'))
        # A labelled fixture verifies the result text, not a generated game seed.
        sample = SeedResult('UI_FIXTURE', 1, origin='scenario.militia', done=True, lines=[
            'CharInfo: 0 Melee:0.9 Hitpoints:60(95)0 Bravery:40(55)0 Stamina:80(115)3 '
            'MeleeSkill:60(95)3 RangedSkill:40(70)0 MeleeDefense:5(35)3 '
            'RangedDefense:0(30)0 Initiative:100(140)0', 'Trait: trait.determined'])
        page._accept_results([sample])
        page.sections.setCurrentIndex(1)
        page.format_combo.setCurrentIndex(page.format_combo.findData('detail'))
        page.table.selectRow(0)
        page.preview_btn.setChecked(True)
        page.resize(1000, 850)
        app.processEvents()
        assert '关张档 · 猛将' in page.detail_label.toPlainText()
        assert '总计9星' in page.detail_label.toPlainText()
        assert page.grab().save(str(output/'rating-fixture.png'))
        report = {'game_started':False,'filters':[840,590], 'result_preview':[page.width(),page.height()],
                  'dialog':[dialog.width(),dialog.height()],'traits':dialog.table.rowCount(),
                  'stars_dialog':[stars.width(),stars.height()], 'controls_in_bounds':True,
                  'fixture_rating':'关张档 · 猛将'}
        (output/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))
        dialog.close()
        stars.close()
        page.close()

if __name__ == '__main__':
    main()
