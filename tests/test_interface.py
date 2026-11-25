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

    def test_filtros_de_pendencia_funcionam_sem_nome_e_com_bairro(self):
        sem_cep = self.ler_json('/api/consulta', pendencia_cep='sem_cep_atual', bairro='Povoado de Marcelânia')
        self.assertEqual(sem_cep['criterio'], 'pendencias')
        self.assertTrue(any(item['nome_municipal_documentado'] == 'Rua Dona Etelvina Rosa de Jesus'
                            and item['cep_publicado'] is None for item in sem_cep['resultados']))
        fila = self.ler_json('/api/consulta', pendencia_cep='cadastro_a_confirmar', bairro='Povoado de Marcelânia')
        self.assertEqual(fila['total'], sem_cep['total'])
        correios = self.ler_json('/api/consulta', q='Rua 216', bairro='Vila Santos Dumont',
                                  pendencia_cep='correios_a_conferir')
        trecho, = correios['resultados']
        self.assertEqual(trecho['cep_publicado'], '75654-216')
        self.assertEqual(trecho['conferencia_correios'], 'pendente')
        geral = self.ler_json('/api/consulta', q='75650-000', pendencia_cep='correios_a_conferir')
        self.assertEqual(geral['total'], 0)
        with self.assertRaises(HTTPError) as erro:
            self.ler_json('/api/consulta', pendencia_cep='invalido')
        erro.exception.close()
        self.assertEqual(erro.exception.code, 400)

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

    def test_cadastro_local_preserva_publicacao_e_busca_nomes_e_ceps(self):
        trecho, = self.ler_json('/api/consulta', q='Rua 216', bairro='Vila Santos Dumont')['resultados']
        dados = {'trecho_id': trecho['trecho_id'], 'nome_anterior': 'Rua 216',
                 'nome_novo': 'Rua de Teste da Memória', 'vigencia_desde': '2026-11-20',
                 'situacao_cep': 'alterado', 'cep_anterior': '75654-216', 'cep_novo': '75659-987',
                 'fonte': 'Comunicado de teste'}
        requisicao = Request(self.url + '/api/mudancas', data=json.dumps(dados).encode(),
                             headers={'Content-Type': 'application/json', 'Origin': self.url})
        with self.assertRaises(HTTPError) as erro:
            urlopen(requisicao, timeout=5)
        self.assertEqual(erro.exception.code, 403)
        erro.exception.close()
        self.servidor.edicao = True
        self.addCleanup(setattr, self.servidor, 'edicao', False)
        for codigo in (201, 200):
            with urlopen(requisicao, timeout=5) as resposta:
                self.assertEqual(resposta.status, codigo)
        for busca in ('Rua de Teste da Memória', '75659-987', 'Rua 216', '75654-216'):
            encontrados = self.ler_json('/api/consulta', q=busca, bairro='Vila Santos Dumont')['resultados']
            atual, = [item for item in encontrados if item['trecho_id'] == trecho['trecho_id']]
            self.assertEqual(atual['cep_publicado'], '75654-216')
            self.assertEqual(atual['conferencia_correios'], 'pendente')
            mudanca, = atual['mudancas_cadastradas']
            self.assertEqual(mudanca['cep_novo'], '75659-987')
        anterior = {**dados, 'nome_anterior': 'Rua de Teste Antiga', 'nome_novo': 'Rua 216',
                    'vigencia_desde': '1980-01-01', 'situacao_cep': 'mantido', 'cep_novo': ''}
        cabecalhos = {'Content-Type': 'application/json', 'Origin': self.url}
        for cadastro, status in (({**anterior, 'vigencia_desde': '1980-02-31'}, 400), (anterior, 201)):
            tentativa = Request(self.url + '/api/mudancas', data=json.dumps(cadastro).encode(), headers=cabecalhos)
            if status == 400:
                with self.assertRaises(HTTPError) as erro:
                    urlopen(tentativa, timeout=5)
                self.assertEqual(erro.exception.code, status)
                erro.exception.close()
            else:
                with urlopen(tentativa, timeout=5) as resposta:
                    self.assertEqual(resposta.status, status)
        antigo, = self.ler_json('/api/consulta', q='Rua de Teste Antiga')['resultados']
        self.assertEqual([m['vigencia_desde'] for m in antigo['mudancas_cadastradas']], ['2026-11-20', '1980-01-01'])
        self.assertEqual(antigo['mudancas_cadastradas'][1]['cep_novo'], '75654-216')
        filtros = {'q': 'Rua 216', 'pendencia_cep': 'cadastro_a_confirmar', 'bairro': 'Vila Santos Dumont'}
        pendente = {**dados, 'nome_novo': 'Rua de Teste com CEP Pendente',
                    'situacao_cep': 'desconhecido', 'cep_novo': ''}
        resolvido = {**pendente, 'situacao_cep': 'alterado', 'cep_novo': '75659-987'}
        for cadastro, total in ((pendente, 1), (resolvido, 0)):
            tentativa = Request(self.url + '/api/mudancas', data=json.dumps(cadastro).encode(), headers=cabecalhos)
            with urlopen(tentativa, timeout=5) as resposta:
                self.assertEqual(resposta.status, 201)
            fila = self.ler_json('/api/consulta', **filtros)
            self.assertEqual(fila['total'], total)
            if total:
                self.assertEqual(fila['resultados'][0]['trecho_id'], trecho['trecho_id'])
        requisicao.add_header('Origin', 'https://outra-origem.example')
        with self.assertRaises(HTTPError) as erro:
            urlopen(requisicao, timeout=5)
        self.assertEqual(erro.exception.code, 403)
        erro.exception.close()
