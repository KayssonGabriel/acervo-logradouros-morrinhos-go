import argparse
import csv
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlsplit

from acervo import BANCO, RAIZ, abrir_banco, consultar, registrar_mudanca


ARQUIVOS = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/estilos.css': ('estilos.css', 'text/css; charset=utf-8'),
    '/consulta.js': ('consulta.js', 'text/javascript; charset=utf-8'),
    '/icones.svg': ('icones.svg', 'image/svg+xml'),
    '/marca.svg': ('marca.svg', 'image/svg+xml'),
}
ATOS_CATALOGADOS = json.loads((RAIZ / 'dados/fontes.json').read_text(encoding='utf-8'))['atos']
FICHAS_PREFEITURA = {ato['id']: ato['ficha_prefeitura'] for ato in ATOS_CATALOGADOS if 'ficha_prefeitura' in ato}
LEIS_LOCAIS = {
    '/' + ato['arquivo']: RAIZ / ato['arquivo']
    for ato in ATOS_CATALOGADOS
    if re.fullmatch(r'fontes/leis/lei-[0-9]+-[0-9]{4}\.pdf', ato['arquivo'])
}
ROTAS = {'/api/consulta', '/api/bairros', '/api/fontes'}
TAMANHO_PAGINA = 20
with (RAIZ / 'fontes/ceps/correios-2026-11-25-consolidado.csv').open(encoding='utf-8-sig', newline='') as arquivo:
    ENDERECOS_CORREIOS = {
        (linha['Logradouro'], linha['Bairro'], linha['CEP'])
        for linha in csv.DictReader(arquivo, delimiter=';') if linha['Localidade'] == 'Morrinhos/GO'
    }
LISTAS = {
    'lista-2025-12-bairro': 'Lista por bairro',
    'lista-2025-12-alfabetica': 'Lista em ordem alfabética',
    'lista-2025-10': 'Lista complementar de CEPs',
    'lista-2025-01': 'Cadastro de logradouros de janeiro de 2025',
    'lista-2025-01-bairro': 'Cadastro por bairro de janeiro de 2025',
    'lista-2024-11': 'Cadastro de logradouros de novembro de 2024',
    'correios-busca-vila-santos-dumont-20261125': 'Busca CEP dos Correios por bairro',
    'comunicado-cep-geral-2025-03': 'Comunicado sobre o CEP geral',
}
CAMPOS_CONSULTA = (
    'variantes_postais',
    'trecho_id', 'bairro', 'trecho_documentado', 'nome_municipal_documentado',
    'nome_postal_publicado', 'cep_publicado', 'fim_uso_geral_anunciado', 'referencia_postal',
    'situacao_historico', 'situacao_postal', 'divergencia_postal', 'conferencia_correios', 'conferido_em',
)
CAMPOS_ATO = ('numero', 'artigo', 'pagina', 'data_ato', 'bairro_no_ato', 'trecho_no_ato',
              'nome_anterior', 'nome_atribuido', 'data_publicacao', 'vigencia_desde', 'nota')
CAMPOS_POSTAIS = ('referencia', 'pagina', 'nome_original', 'bairro_original', 'cep')


def url_publica(url):
    if url in LEIS_LOCAIS:
        return url
    partes = urlsplit(url)
    if partes.scheme == 'https' and partes.hostname and not (partes.username or partes.password):
        return url
    return None


def resultados_publicos(db, params):
    termo = params.get('q', [''])[0].strip()
    bairro = params.get('bairro', [''])[0].strip()
    pendencia_cep = params.get('pendencia_cep', [''])[0]
    pagina = params.get('pagina', ['1'])[0]
    if len(termo) > 120 or len(bairro) > 120:
        raise ValueError('Informe um nome ou CEP de até 120 caracteres.')
    if not re.fullmatch(r'[1-9][0-9]{0,3}', pagina):
        raise ValueError('Página de resultados inválida.')
    pagina = int(pagina)
    dados = consultar(db, termo, bairro or None, limite=TAMANHO_PAGINA,
                      deslocamento=(pagina - 1) * TAMANHO_PAGINA, pendencia_cep=pendencia_cep or None)
    resultados = []
    for trecho in dados['resultados']:
        resumo = {campo: trecho[campo] for campo in CAMPOS_CONSULTA}
        endereco = (trecho['nome_postal_publicado'], trecho['bairro'], trecho['cep_publicado'])
        resumo['nome_postal_nos_correios'] = trecho['conferencia_correios'] == 'confirmado' or (
            trecho['conferencia_correios'] == 'pendente' and endereco in ENDERECOS_CORREIOS
        )
        resumo['historico_nomes'] = [
            {**{campo: ato[campo] for campo in CAMPOS_ATO}, 'url': url_publica(ato['url']),
             'ficha_prefeitura': FICHAS_PREFEITURA.get(ato['fonte_id'])}
            for ato in trecho['historico_nomes']
        ]
        resumo['nomes_historicos'] = [
            {**nome, 'url': url_publica(nome['url'])} for nome in trecho['nomes_historicos']
        ]
        resumo['observacoes_postais'] = [
            {**{campo: observacao[campo] for campo in CAMPOS_POSTAIS},
             'titulo': LISTAS.get(observacao['fonte_id'], 'Lista postal'),
             'url': url_publica(observacao['url'])}
            for observacao in trecho['observacoes_postais']
        ]
        resumo['mudancas_cadastradas'] = [
            {**mudanca, 'url_fonte': url_publica(mudanca['url_fonte']) if mudanca['url_fonte'] else None}
            for mudanca in trecho['mudancas_cadastradas']
        ]
        resultados.append(resumo)
    return {'resultados': resultados, 'total': dados['total'], 'pagina': pagina, 'por_pagina': TAMANHO_PAGINA,
            'criterio': dados['criterio'], 'cep_geral_informado': dados['cep_geral_informado'],
            'conflito_entrada': dados['conflito_entrada']}


def fontes_publicas(db):
    fontes = db.execute('''
        SELECT f.id, f.tipo, f.referencia, f.url, f.abrangencia, min(a.numero) AS numero
        FROM fonte f LEFT JOIN ato_nome a ON a.fonte_id = f.id
        WHERE f.tipo <> 'lista_postal' OR f.referencia >=
            (SELECT max(referencia) FROM fonte WHERE abrangencia = 'integral')
        GROUP BY f.id ORDER BY f.referencia DESC, f.prioridade DESC, f.id
    ''')
    return {'fontes': [
        {'id': fonte['id'], 'tipo': fonte['tipo'], 'referencia': fonte['referencia'],
         'abrangencia': fonte['abrangencia'], 'url': url_publica(fonte['url']),
         'ficha_prefeitura': FICHAS_PREFEITURA.get(fonte['id']),
         'titulo': f"Lei nº {fonte['numero']}" if fonte['numero'] else LISTAS.get(fonte['id'], 'Fonte postal')}
        for fonte in fontes
    ]}


class InterfaceHandler(BaseHTTPRequestHandler):
    server_version = 'AcervoLocal'
    sys_version = ''

    def log_request(self, code='-', size='-'):
        # Os termos consultados podem ter sido copiados de documentos internos.
        pass

    def responder(self, codigo, conteudo, mime):
        self.send_response(codigo)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(conteudo)))
        self.send_header('Cache-Control', 'no-store' if mime.startswith('application/json') else 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy',
                         "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
                         "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(conteudo)

    def json(self, codigo, dados):
        self.responder(codigo, json.dumps(dados, ensure_ascii=False).encode('utf-8'),
                       'application/json; charset=utf-8')

    def do_POST(self):
        self.close_connection = True
        if self.path != '/api/mudancas':
            self.json(HTTPStatus.NOT_FOUND, {'erro': 'Página não encontrada.'})
            return
        porta = self.server.server_port
        host = self.headers.get('Host')
        origens = self.headers.get_all('Origin', [])
        if (not self.server.edicao or host not in (f'127.0.0.1:{porta}', f'localhost:{porta}')
                or origens != [f'http://{host}']):
            self.json(HTTPStatus.FORBIDDEN, {'erro': 'O cadastro exige o modo de edição e a interface local.'})
            return
        tamanho = self.headers.get('Content-Length', '')
        if (self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding')
                or len(self.headers.get_all('Content-Length', [])) != 1
                or not re.fullmatch(r'[0-9]{1,5}', tamanho) or not 0 < int(tamanho) <= 16384):
            self.json(HTTPStatus.BAD_REQUEST, {'erro': 'O cadastro deve conter um JSON de até 16 KiB.'})
            return
        try:
            self.connection.settimeout(5)
            dados = json.loads(self.rfile.read(int(tamanho)).decode('utf-8'))
            with closing(abrir_banco(self.server.banco, escrita=True)) as db:
                resultado = registrar_mudanca(db, dados)
            self.json(HTTPStatus.CREATED if resultado['criado'] else HTTPStatus.OK, resultado)
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            self.json(HTTPStatus.BAD_REQUEST, {'erro': 'JSON inválido.'})
        except ValueError as erro:
            self.json(HTTPStatus.BAD_REQUEST, {'erro': str(erro)})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return
        except (OSError, sqlite3.Error):
            self.json(HTTPStatus.SERVICE_UNAVAILABLE, {'erro': 'Não foi possível gravar o cadastro no banco local.'})

    def do_GET(self):
        porta = self.server.server_port
        if self.headers.get('Host') not in (f'127.0.0.1:{porta}', f'localhost:{porta}'):
            self.json(HTTPStatus.FORBIDDEN, {'erro': 'Use o endereço local do acervo.'})
            return
        try:
            alvo = urlsplit(self.path)
            if alvo.scheme or alvo.netloc:
                raise ValueError('Endereço de consulta inválido.')
            if alvo.path in ARQUIVOS:
                arquivo, mime = ARQUIVOS[alvo.path]
                self.responder(HTTPStatus.OK, (RAIZ / 'web' / arquivo).read_bytes(), mime)
            elif alvo.path in LEIS_LOCAIS:
                self.responder(HTTPStatus.OK, LEIS_LOCAIS[alvo.path].read_bytes(), 'application/pdf')
            elif alvo.path in ROTAS:
                self.json(HTTPStatus.OK, self.consultar_api(alvo))
            else:
                self.json(HTTPStatus.NOT_FOUND, {'erro': 'Página não encontrada.'})
        except ValueError as erro:
            self.json(HTTPStatus.BAD_REQUEST, {'erro': str(erro)})
        except (BrokenPipeError, ConnectionResetError):
            return
        except (OSError, sqlite3.Error):
            self.json(HTTPStatus.SERVICE_UNAVAILABLE, {'erro': 'A base local está indisponível.'})

    def consultar_api(self, alvo):
        params = parse_qs(alvo.query, max_num_fields=8)
        with closing(abrir_banco(self.server.banco)) as db:
            if alvo.path == '/api/consulta':
                return {**resultados_publicos(db, params), 'edicao_habilitada': self.server.edicao}
            if alvo.path == '/api/fontes':
                return fontes_publicas(db)
            return {'bairros': [linha['nome'] for linha in db.execute('SELECT nome FROM bairro ORDER BY chave')]}


def criar_servidor(banco, porta, *, edicao=False):
    servidor = ThreadingHTTPServer(('127.0.0.1', porta), InterfaceHandler)
    servidor.banco = banco
    servidor.edicao = edicao
    return servidor


def main():
    cli = argparse.ArgumentParser(description='Interface local de consulta do acervo de Morrinhos (GO)')
    cli.add_argument('--banco', type=Path, default=BANCO)
    cli.add_argument('--porta', type=int, default=8765)
    cli.add_argument('--edicao', action='store_true', help='Permite cadastrar mudanças nesta interface local.')
    args = cli.parse_args()
    if not 0 <= args.porta <= 65535:
        cli.error('Informe uma porta entre 0 e 65535.')
    try:
        with closing(abrir_banco(args.banco)), criar_servidor(args.banco, args.porta, edicao=args.edicao) as servidor:
            modo = 'Consulta e edição' if args.edicao else 'Consulta'
            print(f'{modo} local em http://127.0.0.1:{servidor.server_port}', flush=True)
            servidor.serve_forever()
    except KeyboardInterrupt:
        return
    except (OSError, sqlite3.Error, ValueError):
        cli.exit(1, 'Não foi possível iniciar a consulta. Confira a porta e prepare a base com acervo.py importar.\n')


if __name__ == '__main__':
    main()
