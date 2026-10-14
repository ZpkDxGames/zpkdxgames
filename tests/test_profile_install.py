import importlib.util, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('dashboard_entry',ROOT/'scripts/profile_dashboard.py')
entry=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(entry)

class InstallTests(unittest.TestCase):
    def test_failed_install_restores_previous_tree(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as sd:
            root=Path(td); staged=Path(sd)
            (root/'assets/profile-dashboard').mkdir(parents=True); (root/'assets/profile-dashboard/old.svg').write_text('old')
            (root/'data').mkdir(); (root/'README.md').write_text('old readme'); (root/'data/profile.json').write_text('old data')
            (staged/'new.svg').write_text('new')
            real_replace=entry.os.replace; calls={'n':0}
            def fail_second(src,dst):
                calls['n']+=1
                if calls['n']==2: raise OSError('simulated install failure')
                return real_replace(src,dst)
            with patch.object(entry.os,'replace',fail_second):
                with self.assertRaises(OSError): entry.install(staged,'new readme','new data',root)
            self.assertEqual((root/'README.md').read_text(),'old readme')
            self.assertEqual((root/'data/profile.json').read_text(),'old data')
            self.assertEqual((root/'assets/profile-dashboard/old.svg').read_text(),'old')
            self.assertFalse((root/'assets/profile-dashboard/new.svg').exists())

if __name__=='__main__': unittest.main()