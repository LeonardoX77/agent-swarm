import unittest
from pathlib import Path
DOCS=Path(__file__).parents[3]/'docs'/'runbooks'/'agent-fabric'
class RunbookSafetyTests(unittest.TestCase):
 def test_all_runbooks_have_safe_operator_sections(self):
  headings=['## Propósito','## No objetivos','## Entradas','## Preflight seguro','## Evidencia que conservar','## Acciones aplazadas','## Condiciones de detención por falla','## Pasos futuros autorizados']
  for name in ('macbook.md','mac-mini.md','orchestration.md','validation-recovery.md'):
   content=(DOCS/name).read_text(); self.assertTrue(all(item in content for item in headings),name); self.assertIn('DEFERRED',content)
 def test_documentation_preserves_security_boundaries(self):
  content='\n'.join(path.read_text() for path in DOCS.glob('*.md'))
  for text in ('/Users/leo/projects','Git','habilidades locales','BatchMode=yes','no se crea','no se debe eliminar'):
   self.assertIn(text.lower(),content.lower())
  self.assertNotIn('--apply',content)
 def test_documentation_uses_observability_without_lock_enforcement(self):
  paths=tuple(DOCS.glob('*.md'))+(Path(__file__).parents[3]/'docs'/'odd'/'agent-fabric-foundation.md',)
  content='\n'.join(path.read_text() for path in paths).lower()
  for text in ('fabric-activity','observabilidad','no autoriza','no bloquea','sanead'):
   self.assertIn(text,content)
  for text in ('fabric-lock','lock','bloqueo','contención','contention','fencing','ssh-based locking'):
   self.assertNotIn(text,content)
if __name__=='__main__': unittest.main()
