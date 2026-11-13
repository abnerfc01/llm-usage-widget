import tempfile, unittest
from pathlib import Path
from scripts.configurar_provedores import carregar, salvar, adicionar, alterar

class ConfiguradorTest(unittest.TestCase):
    def test_preserva_config_e_altera_somente_conta(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'; c=carregar(p); c['extra']='mantido'; salvar(p,c)
            alterar(c,'codex',visible=False,collection_interval_seconds=900); salvar(p,c)
            r=carregar(p); self.assertEqual(r['extra'],'mantido'); self.assertFalse(next(x for x in r['providers'] if x['id']=='codex')['visible'])
    def test_adicionar_e_impedir_duplicatas(self):
        with tempfile.TemporaryDirectory() as d:
            c=carregar(Path(d)/'ausente'); adicionar(c,'deepseek','DeepSeek','metered')
            p=next(x for x in c['providers'] if x['id']=='deepseek'); self.assertEqual(p['plugin'],'metered_generic'); self.assertFalse(p['enabled'])
            with self.assertRaises(ValueError): adicionar(c,'deepseek','Outro','quota')
            with self.assertRaises(ValueError): adicionar(c,'../inseguro','Outro','quota')
