import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from interface import criar_servidor


RAIZ = Path(__file__).resolve().parents[1]


class TestInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pasta = tempfile.TemporaryDirectory()
        cls.addClassCleanup(pasta.cleanup)
        banco = Path(pasta.name) / 'acervo.sqlite3'
        subprocess.run([sys.executable, '-X', 'utf8', 'acervo.py', '--banco', str(banco), 'importar'],
                       cwd=RAIZ, capture_output=True, check=True)
        cls.servidor = criar_servidor(banco, 0)
        cls.addClassCleanup(cls.servidor.server_close)
        thread = Thread(target=cls.servidor.serve_forever, daemon=True)
        thread.start()
        cls.addClassCleanup(thread.join)
        cls.addClassCleanup(cls.servidor.shutdown)
        cls.url = f'http://127.0.0.1:{cls.servidor.server_port}'

    def ler_json(self, caminho, **params):
        with urlopen(f'{self.url}{caminho}?{urlencode(params)}', timeout=5) as resposta:
            return json.load(resposta)

    def test_busca_com_historico_expoe_somente_dados_de_consulta(self):
        dados = self.ler_json('/api/consulta', q='R. 03, Jardim América')
        trecho, = dados['resultados']
        self.assertEqual(trecho['cep_publicado'], '75650-281')
        self.assertEqual(trecho['historico_nomes'][0]['nome_anterior'], 'Rua 03')
        self.assertEqual(trecho['conferencia_correios'], 'pendente')
        self.assertNotIn('evidencia_conferencia', trecho)
        self.assertNotIn('arquivo', trecho['observacoes_postais'][0])

    def test_paginacao_preserva_contagem_total(self):
        primeira = self.ler_json('/api/consulta', q='Rua', pagina=1)
        segunda = self.ler_json('/api/consulta', q='Rua', pagina=2)
        self.assertEqual(primeira['total'], segunda['total'])
        self.assertGreater(primeira['total'], len(primeira['resultados']))
        self.assertNotEqual(primeira['resultados'][0]['trecho_id'], segunda['resultados'][0]['trecho_id'])

    def test_api_distingue_sugestao_de_correspondencia_documentada(self):
        dados = self.ler_json('/api/consulta', q='Rua Juvercna', bairro='Jardim América')
        self.assertEqual(dados['criterio'], 'aproximada')
        self.assertTrue(any(trecho['cep_publicado'] == '75650-281' for trecho in dados['resultados']))

    def test_interface_e_fontes_sao_servidas_pelo_mesmo_host(self):
        with urlopen(self.url, timeout=5) as resposta:
            self.assertIn('Consulta de logradouros', resposta.read().decode('utf-8'))
            self.assertEqual(resposta.headers['X-Content-Type-Options'], 'nosniff')
        dados = self.ler_json('/api/fontes')
        self.assertTrue(any(fonte['id'] == 'lista-2025-12-bairro' for fonte in dados['fontes']))

    def test_bloqueia_hosts_externos_e_arquivos_do_acervo(self):
        for caminho, cabecalho, codigo in (('/', {'Host': 'outro.example'}, 403),
                                           ('/morrinhos.sqlite3', {}, 404),
                                           ('/api/consulta', {}, 400)):
            with self.subTest(caminho=caminho), self.assertRaises(HTTPError) as retorno:
                urlopen(Request(self.url + caminho, headers=cabecalho), timeout=5)
            self.assertEqual(retorno.exception.code, codigo)
            retorno.exception.close()
